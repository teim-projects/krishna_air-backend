from django.db.models import Q

from lead_management.models import Customer


def build_customer_features():
    """
    Build generic customer-level behavioral features.

    The analytics engine works with customer-level feature data,
    so CRM-specific model relationships stay inside this adapter.
    """

    customer_features = []

    for customer in Customer.objects.all():
        leads = customer.leads.all()

        lead_count = leads.count()

        active_leads = leads.filter(
            Q(status="open") | Q(status="in_process")
        ).count()

        followup_count = sum(
            lead.followups.count()
            for lead in leads
        )

        invoices = customer.invoices.all()

        transaction_count = invoices.count()

        revenue = sum(
            float(invoice.grand_total or 0)
            for invoice in invoices
        )

        customer_features.append(
            {
                "customer_id": customer.id,
                "customer_name": customer.name,
                "lead_count": lead_count,
                "active_leads": active_leads,
                "followup_count": followup_count,
                "transaction_count": transaction_count,
                "revenue": revenue,
            }
        )

    return customer_features