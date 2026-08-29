from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Q
from api.models import CustomUser, Notification
from lead_management.models import lead_management
from quotation.models import Quotation

@receiver(pre_save, sender=lead_management)
def cache_old_assignee(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = lead_management.objects.get(pk=instance.pk)
            instance._old_assign_to_id = old_instance.assign_to_id
        except lead_management.DoesNotExist:
            instance._old_assign_to_id = None
    else:
        instance._old_assign_to_id = None

@receiver(post_save, sender=lead_management)
def lead_notification(sender, instance, created, **kwargs):
    if created:
        recipients = set()
        if instance.assign_to:
            recipients.add(instance.assign_to)
        
        # Get all staff, superusers, and admin/sub-admin role users
        staff_and_admins = CustomUser.objects.filter(
            Q(is_staff=True) | 
            Q(is_superuser=True) | 
            Q(role__name__iexact='admin') | 
            Q(role__name__iexact='sub-admin')
        )
        for user in staff_and_admins:
            recipients.add(user)

        # Get source display name
        lead_source_map = {
            'google_ads': 'Google Ads',
            'indiamart': 'IndiaMART',
            'bni': 'BNI',
            'justdial': 'Justdial',
            'reference': 'Reference',
            'architect/interior_designer': 'Architect / Interior Designer',
            'builder': 'Builder',
            'existing_customer': 'Existing Customer',
            'ka_staff': 'KA Staff',
            'other': 'Other',
        }
        source_display = lead_source_map.get(instance.lead_source, instance.lead_source or "Other")

        for user in recipients:
            if user:
                Notification.objects.create(
                    recipient=user,
                    notification_type='LEAD',
                    tag='NEW LEAD',
                    title="New Enquiry / Lead Added",
                    description=f"New lead added: {instance.customer.name} via {source_display}.",
                    reference_type='lead',
                    reference_id=instance.id,
                    is_read=False
                )
    else:
        old_assign_to_id = getattr(instance, '_old_assign_to_id', None)
        if instance.assign_to and instance.assign_to_id != old_assign_to_id:
            # Notify the new assignee
            Notification.objects.create(
                recipient=instance.assign_to,
                notification_type='LEAD',
                tag='ASSIGNED',
                title="New Lead Assigned",
                description=f"Lead #{instance.id} for {instance.customer.name} has been assigned to you.",
                reference_type='lead',
                reference_id=instance.id,
                is_read=False
            )
            
            # Notify all admins as well about the reassignment
            admins = CustomUser.objects.filter(
                Q(is_staff=True) | 
                Q(is_superuser=True) | 
                Q(role__name__iexact='admin') | 
                Q(role__name__iexact='sub-admin')
            ).exclude(id=instance.assign_to.id)
            
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notification_type='LEAD',
                    tag='ASSIGNED',
                    title="Lead Reassigned",
                    description=f"Lead #{instance.id} for {instance.customer.name} has been assigned to {instance.assign_to.first_name}.",
                    reference_type='lead',
                    reference_id=instance.id,
                    is_read=False
                )

@receiver(post_save, sender=Quotation)
def new_quotation_notification(sender, instance, created, **kwargs):
    if created:
        # Notify staff / admins
        staff_and_admins = CustomUser.objects.filter(
            Q(is_staff=True) | 
            Q(is_superuser=True) | 
            Q(role__name__iexact='admin') | 
            Q(role__name__iexact='sub-admin')
        ).distinct()
        for user in staff_and_admins:
            if user:
                Notification.objects.create(
                    recipient=user,
                    notification_type='QUOTATION',
                    tag='NEW QUOTATION',
                    title="New Quotation Created",
                    description=f"Quotation {instance.quotation_no} for {instance.customer.name} has been created.",
                    reference_type='quotation',
                    reference_id=instance.id,
                    is_read=False
                )
