from django.db import models
from api.models import SiteManagement, BranchManagement
from product_management.models import ProductVariant, item

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


# --------------------------------------------------------------------------------
# Terms and Conditions Management model
# --------------------------------------------------------------------------------
class TermsConditionType(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name


class TermsConditions(models.Model):
    terms_condition_type = models.ForeignKey(
        TermsConditionType,
        on_delete=models.CASCADE,
        related_name="conditions"
    )
    terms = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.terms_condition_type.name} - {self.terms[:40]}"



# --------------------------------------------------------------------------------
# Purchase Order Management model
# --------------------------------------------------------------------------------

class PurchaseOrder(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="purchase_orders")
    site = models.ForeignKey(SiteManagement, on_delete=models.PROTECT, related_name="purchase_orders", null=True, blank=True)
    branch = models.ForeignKey(BranchManagement, on_delete=models.PROTECT, related_name="purchase_orders")
    terms_conditions = models.ForeignKey(TermsConditions, on_delete=models.PROTECT, related_name="purchase_orders")
    purchase_order_no = models.CharField(max_length=50 , unique=True)
    quotation_ref_no = models.CharField(max_length=50, blank=True, null=True)
    quotation_date = models.DateField(null=True, blank=True)
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_no = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.purchase_order_no
    


class PurchaseOrderProduct(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, 
        on_delete=models.CASCADE,
        related_name="products"
    )

    # For ACs use ProductVariant, for parts use item
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, null=True, blank=True)
    item = models.ForeignKey(item, on_delete=models.PROTECT, null=True, blank=True)

    description = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    uom = models.CharField(max_length=20)

    rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)