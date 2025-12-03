from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import *



@receiver(pre_save, sender=Customer)
def copy_address_to_site(sender, instance: Customer, **kwargs):
    # if flag set and site_address empty, copy address fields
    if instance.both_address_is_same:
        # Only copy when site fields are empty or you explicitly want to overwrite:
        if not instance.site_address:
            instance.site_address = instance.address
        if not instance.site_city:
            instance.site_city = instance.city
        if not instance.site_state:
            instance.site_state = instance.state
        if not instance.site_pin_code:
            instance.site_pin_code = instance.pin_code 