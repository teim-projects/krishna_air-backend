"""Generate and sync AMC service visit rows from contract frequency."""
from datetime import timedelta

from django.db import transaction

from .models import AMCServiceVisit, ServiceManagementRecord


def get_service_record_for_amc_contract(contract):
    """Match active AMC service management row for this contract's customer."""
    from django.db.models import Q

    customer = contract.customer
    if not customer:
        return None

    qs = ServiceManagementRecord.objects.filter(
        contract_type='amc',
        contract_status='active',
    ).filter(
        Q(customer_id=customer.id) | Q(customer_name__iexact=customer.name)
    )

    if contract.amc_type:
        typed = qs.filter(amc_service_type=contract.amc_type)
        if typed.exists():
            qs = typed

    return qs.order_by('-created_at').first()


def planned_dates_for_contract(contract, visit_count):
    """Evenly spread planned visit dates between AMC start and end (inclusive)."""
    start = contract.amc_start_date
    end = contract.amc_end_date
    if not start or not end or visit_count < 1:
        return []

    if visit_count == 1:
        return [start]

    total_days = (end - start).days
    if total_days <= 0:
        return [start] * visit_count

    dates = []
    for i in range(visit_count):
        if i == visit_count - 1:
            dates.append(end)
        else:
            offset = round(i * total_days / (visit_count - 1))
            dates.append(start + timedelta(days=offset))
    return dates


@transaction.atomic
def sync_amc_service_visits(contract):
    """
    Create or refresh scheduled visits for an AMC contract.
    - Visit count comes from get_expected_visit_count() (Quarterly + 1yr => 4).
    - Does not delete visits already linked to a technician work record.
    - Updates planned_date on remaining scheduled-only rows.
    """
    visit_count = contract.get_expected_visit_count()
    if visit_count < 1:
        contract.service_visits.filter(technician_work_record__isnull=True).delete()
        return []

    service_record = get_service_record_for_amc_contract(contract)
    planned_dates = planned_dates_for_contract(contract, visit_count)
    visit_amounts = contract.split_visit_amounts()

    protected_numbers = set(
        contract.service_visits.filter(technician_work_record__isnull=False).values_list(
            'visit_number', flat=True
        )
    )

    contract.service_visits.filter(
        technician_work_record__isnull=True,
        status=AMCServiceVisit.STATUS_SCHEDULED,
    ).delete()

    created_or_updated = []
    for index, planned_date in enumerate(planned_dates, start=1):
        visit_amount = visit_amounts[index - 1] if index - 1 < len(visit_amounts) else 0

        if index in protected_numbers:
            visit = contract.service_visits.filter(visit_number=index).first()
            if visit:
                update_fields = ['updated_at']
                if visit.service_record_id is None and service_record:
                    visit.service_record = service_record
                    update_fields.append('service_record')
                # Keep allocated visits' amount in sync with current AMC cost split
                if visit.amount != visit_amount:
                    visit.amount = visit_amount
                    update_fields.append('amount')
                visit.save(update_fields=update_fields)
                created_or_updated.append(visit)
            continue

        visit, _ = AMCServiceVisit.objects.update_or_create(
            amc_contract=contract,
            visit_number=index,
            defaults={
                'planned_date': planned_date,
                'amount': visit_amount,
                'service_record': service_record,
                'status': AMCServiceVisit.STATUS_SCHEDULED,
            },
        )
        created_or_updated.append(visit)

    contract.service_visits.filter(
        visit_number__gt=visit_count,
        technician_work_record__isnull=True,
    ).delete()

    return created_or_updated


def close_amc_contract_if_all_visits_completed(contract):
    """When every planned visit is COMPLETED, mark the AMC contract CLOSED."""
    if not contract or contract.status == 'CLOSED':
        return contract
    total = contract.service_visits.count()
    if total < 1:
        return contract
    pending = contract.service_visits.exclude(status=AMCServiceVisit.STATUS_COMPLETED).exists()
    if not pending:
        contract.status = 'CLOSED'
        contract.save(update_fields=['status', 'updated_at'])
    return contract


def close_service_record_if_work_completed(work_record):
    """
    Close linked ServiceManagementRecord when work is completed.
    - AMC: only after all planned visits on the AMC contract are COMPLETED
    - one_time / warranty: when all work records are completed (and expected
      visit count is met if service_frequency_count is set)
    """
    if not work_record or work_record.payment_status != 'completed':
        return None

    visit = getattr(work_record, 'amc_service_visit', None)
    if visit:
        close_amc_contract_if_all_visits_completed(visit.amc_contract)
        if visit.amc_contract.service_visits.exclude(
            status=AMCServiceVisit.STATUS_COMPLETED
        ).exists():
            return None

    service = work_record.service_record
    if not service or service.contract_status == 'closed':
        return service

    if service.contract_type == 'amc':
        service.contract_status = 'closed'
        service.save(update_fields=['contract_status', 'updated_at'])
        return service

    if service.contract_type in ('one_time', 'warranty'):
        if service.technician_work_records.exclude(payment_status='completed').exists():
            return None
        expected = service.service_frequency_count or 0
        if expected > 0:
            done = service.technician_work_records.filter(payment_status='completed').count()
            if done < expected:
                return None
        service.contract_status = 'closed'
        service.save(update_fields=['contract_status', 'updated_at'])
        return service

    return None
