from django.db import models


class Vendor(models.Model):
    # Required fields
    name = models.CharField(max_length=200)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    office_address = models.TextField()
    gst_details = models.CharField(max_length=15)
    office_poc_name = models.CharField(max_length=100)
    office_poc_phone = models.CharField(max_length=15)
    
    # Optional fields
    company_type = models.CharField(max_length=100, blank=True, null=True)
    store_address = models.TextField(blank=True, null=True)
    supplier_category = models.CharField(max_length=100, blank=True, null=True)
    pan_details = models.CharField(max_length=10, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    state_code = models.CharField(max_length=10, blank=True, null=True)
    store_poc_name = models.CharField(max_length=100, blank=True, null=True)
    store_poc_phone = models.CharField(max_length=15, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    bank_details = models.TextField(blank=True, null=True)
    
    # Auto-generated fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


