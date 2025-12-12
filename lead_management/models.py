from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
# Create your models here.
User = get_user_model()

class Customer(models.Model):
  name = models.CharField(max_length=200)
  contact_number = models.CharField(max_length=20, blank=True, null=True)
  email = models.EmailField(blank=True, null=True)
  poc_name = models.CharField(max_length=200, blank=True, null=True)
  poc_contact_number = models.CharField(max_length=20, blank=True, null=True)
  land_line_no = models.CharField(max_length=50 , blank=True, null=True)
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
  project_name = models.CharField(max_length=100, blank=True, null=True)
  project_adderess = models.CharField(max_length=500, blank=True, null=True)
  creatd_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='lead_created')

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

class LeadFollowUp(models.Model):
    lead = models.ForeignKey(
        lead_management,
        on_delete=models.CASCADE,
        related_name='followups'
    )
    followup_date = models.DateField()
    next_followup_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=200,
        choices=LeadStatus.choices,
        default=LeadStatus.OPEN,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_followups_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Follow-up for Lead #{self.lead_id} on {self.followup_date}"

    def save(self, *args, **kwargs):
        # first save the followup itself
        super().save(*args, **kwargs)

        # ---- update main lead from this followup ----
        lead = self.lead

        # status always comes from followup
        lead.status = self.status

        # followup_date on lead = next_followup_date if given, else this followup_date
        lead.followup_date = self.next_followup_date or self.followup_date

        # optionally override remarks if you want the latest remarks on lead
        if self.remarks:
            lead.remarks = self.remarks

        lead.save(update_fields=["status", "followup_date", "remarks"])
   
class LeadFAQ(models.Model):
    """
    Master list of standard FAQ questions for leads.
    Example: "Customer budget?", "Decision maker name?"
    """
    question = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.question


class LeadFollowUpFAQAnswer(models.Model):
    """
    Stores answers to standard FAQs for a particular follow-up.
    """
    followup = models.ForeignKey(
        LeadFollowUp,
        on_delete=models.CASCADE,
        related_name='faq_answers'
    )
    faq = models.ForeignKey(
        LeadFAQ,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    answer = models.TextField(blank=True)

    class Meta:
        unique_together = ('followup', 'faq')

    def __str__(self):
        return f"Q: {self.faq.question} | Lead #{self.followup.lead_id}"
    

