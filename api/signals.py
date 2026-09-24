from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Q
from api.models import CustomUser, Notification
from lead_management.models import lead_management
from quotation.models import Quotation

@receiver(pre_save, sender=lead_management)
def cache_old_assignee(sender, instance, **kwargs):
    """Store the old assign_to_id before save so post_save can detect changes."""
    if instance.pk:
        try:
            old_instance = lead_management.objects.get(pk=instance.pk)
            instance._old_assign_to_id = old_instance.assign_to_id
        except lead_management.DoesNotExist:
            instance._old_assign_to_id = None
    else:
        instance._old_assign_to_id = None


# ── helpers ────────────────────────────────────────────────────────────────────

def _source_display(lead_source):
    lead_source_map = {
        'google_ads':                 'Google Ads',
        'indiamart':                  'IndiaMART',
        'bni':                        'BNI',
        'justdial':                   'Justdial',
        'reference':                  'Reference',
        'architect/interior_designer':'Architect / Interior Designer',
        'builder':                    'Builder',
        'existing_customer':          'Existing Customer',
        'ka_staff':                   'KA Staff',
        'other':                      'Other',
    }
    return lead_source_map.get(lead_source, lead_source or 'Other')


def _admin_users(exclude_id=None):
    """
    Return only true admin-level users: superusers and users with
    admin or sub-admin roles.

    NOTE: is_staff is intentionally excluded here because it is set to True
    on ALL staff accounts (including sales users) during registration
    (api/serializers.py StaffRegisterSerializer.create). Using is_staff would
    incorrectly broadcast admin-only notifications to sales users.
    """
    qs = CustomUser.objects.filter(
        Q(is_superuser=True) |
        Q(role__name__iexact='admin') |
        Q(role__name__iexact='sub-admin')
    ).distinct()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs


# ── Lead notifications ─────────────────────────────────────────────────────────

@receiver(post_save, sender=lead_management)
def lead_notification(sender, instance, created, **kwargs):

    if created:
        source_display = _source_display(instance.lead_source)
        customer_name  = instance.customer.name

        # 1. Personal notification for the assigned salesperson (if any)
        if instance.assign_to:
            Notification.objects.create(
                recipient=instance.assign_to,
                notification_type='LEAD',
                tag='ASSIGNED',
                title='New Lead Assigned to You',
                description=(
                    f"A new lead has been assigned to you: {customer_name} "
                    f"via {source_display}. Please follow up."
                ),
                reference_type='lead',
                reference_id=instance.id,
                is_read=False,
            )

        # 2. Broadcast to all admins / staff
        #    Exclude the assignee if they are also an admin to avoid duplicate.
        exclude_id = instance.assign_to_id if instance.assign_to_id else None
        admins = _admin_users(exclude_id=exclude_id)
        assignee_name = (
            f"{instance.assign_to.first_name} {instance.assign_to.last_name}".strip()
            if instance.assign_to else "Unassigned"
        )
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notification_type='LEAD',
                tag='NEW LEAD',
                title='New Enquiry / Lead Added',
                description=(
                    f"New lead added: {customer_name} via {source_display}."
                    + (f" Assigned to: {assignee_name}." if instance.assign_to else " Not yet assigned.")
                ),
                reference_type='lead',
                reference_id=instance.id,
                is_read=False,
            )

    else:
        # ── Reassignment notification ──────────────────────────────────────────
        old_assign_to_id = getattr(instance, '_old_assign_to_id', None)
        new_assign_to_id = instance.assign_to_id

        if new_assign_to_id and new_assign_to_id != old_assign_to_id:
            customer_name = instance.customer.name

            # Notify the newly assigned salesperson
            Notification.objects.create(
                recipient=instance.assign_to,
                notification_type='LEAD',
                tag='ASSIGNED',
                title='New Lead Assigned to You',
                description=(
                    f"Lead #{instance.id} for {customer_name} has been assigned to you. "
                    f"Please follow up."
                ),
                reference_type='lead',
                reference_id=instance.id,
                is_read=False,
            )

            # Notify admins about the reassignment (exclude the new assignee)
            assignee_name = (
                f"{instance.assign_to.first_name} {instance.assign_to.last_name}".strip()
                or instance.assign_to.email
            )
            for admin in _admin_users(exclude_id=new_assign_to_id):
                Notification.objects.create(
                    recipient=admin,
                    notification_type='LEAD',
                    tag='REASSIGNED',
                    title='Lead Reassigned',
                    description=(
                        f"Lead #{instance.id} for {customer_name} has been "
                        f"reassigned to {assignee_name}."
                    ),
                    reference_type='lead',
                    reference_id=instance.id,
                    is_read=False,
                )


# ── Quotation notifications ────────────────────────────────────────────────────

@receiver(post_save, sender=Quotation)
def new_quotation_notification(sender, instance, created, **kwargs):
    if created:
        for user in _admin_users():
            Notification.objects.create(
                recipient=user,
                notification_type='QUOTATION',
                tag='NEW QUOTATION',
                title='New Quotation Created',
                description=(
                    f"Quotation {instance.quotation_no} for {instance.customer.name} "
                    f"has been created."
                ),
                reference_type='quotation',
                reference_id=instance.id,
                is_read=False,
            )
