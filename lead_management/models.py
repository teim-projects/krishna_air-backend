from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
# Create your models here.
User = get_user_model()




class Customer(models.Model):
  name = models.CharField(max_length=200)
  contact_number = models.CharField(max_length=20, blank=True, null=True)
  email = models.EmailField(blank=True, null=True)
  address = models.TextField(blank=True)
  city = models.CharField(max_length=100,blank=True)
  state = models.CharField(max_length=100, blank=True)
  pin_code = models.CharField(max_length=10, blank=True, null=True)
  both_address_is_same = models.BooleanField(default=False)
  site_address = models.TextField(blank=True, null=True)
  site_city = models.CharField(max_length=100, blank=True, null=True)
  site_state = models.CharField(max_length=100, blank=True, null=True)
  site_pin_code = models.CharField(max_length=10, blank=True, null=True)

  def __str__(self):
        return f"{self.name} ({self.email or self.contact_number or ''})"


  
class LeadSource(models.TextChoices):
    GOOGLE_ADS = 'google_ads', 'Google Ads'
    INDIAMART = 'indiamart', 'IndiaMART'
    BNI = 'bni', 'BNI'
    OTHER = 'other', 'Other'


class LeadStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    CLOSED = 'closed', 'Closed'
    IN_PROCESS = 'in_process', 'In Process'

class lead_management(models.Model):
  customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='leads')
  requirements_details = models.TextField(blank=True)
  hvac_application = models.CharField(max_length=200, blank=True)
  capacity_required =  models.CharField(max_length=200, blank=True)
  lead_source = models.CharField(max_length=200, choices=LeadSource)
  status = models.CharField(max_length=200, choices=LeadStatus)
  assign_to = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='lead_assignment')
  date = models.DateField(blank=True, null=True)
  followup_date = models.DateField(blank=True, null=True)
  remarks = models.TextField(blank=True, null=True)

  def __str__(self):
        return f"Lead #{self.pk} - {self.customer.name or self.customer.email or self.customer.contact_number} - {self.get_status_display()}"

  def clean(self):
      # basic validation: followup_date should not be before date
      if self.date and self.followup_date and self.followup_date < self.date:
          raise ValidationError({"followup_date": "followup_date cannot be before date."})
  
  def save(self, *args, **kwargs):
      # call full_clean to trigger model validation before saving (optional)
      self.full_clean()
      super().save(*args, **kwargs)

   
