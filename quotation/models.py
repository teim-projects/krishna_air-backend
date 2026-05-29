from django.db import models
from django.contrib.auth import get_user_model
from product_management.models import ProductVariant ,item

User = get_user_model()

# Create your models here.
class Quotation(models.Model):

    quotation_no = models.CharField(max_length=50, unique=True)

    customer = models.ForeignKey(
        "lead_management.Customer",
        on_delete=models.PROTECT,
        related_name="quotations"
    )

    branch = models.ForeignKey(
        "api.BranchManagement",
        on_delete=models.PROTECT,
        related_name="quotations",
        null=True,
        blank=True
    )
    
    site = models.ForeignKey(
        "api.SiteManagement",
        on_delete=models.PROTECT,
        related_name="quotations",
        null=True,
        blank=True
    )
    
    terms_conditions = models.ManyToManyField(
        "inventory.TermsConditions",
        related_name="quotations",
        blank=True
    )

    subject = models.CharField(max_length=255)
    site_name = models.CharField(max_length=255, blank=True, null=True)
    thank_you_note = models.TextField(max_length=400)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.quotation_no



class QuotationVersion(models.Model):

    GST_TYPE_CHOICES = (
        ("CGST_SGST", "CGST + SGST"),
        ("IGST", "IGST"),
    )

    quotation = models.ForeignKey(
        Quotation,
        related_name="versions",
        on_delete=models.CASCADE
    )

    version_no = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    gst_type = models.CharField(
        max_length=20,
        choices=GST_TYPE_CHOICES,
        default="CGST_SGST"
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

   

    
    # GRAND TOTAL
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)


    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "version_no"],
                name="unique_quotation_version"
            )
        ]





class QuotationHighSideItem(models.Model):

    quotation_version = models.ForeignKey(
        QuotationVersion,
        related_name="high_side_items",
        on_delete=models.CASCADE
    )

    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    unit = models.CharField(max_length=20, default="NOS")

    mathadi_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transportation_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    hsn_sac = models.CharField(max_length=50, null=True, blank=True)

    # 🔥 NEW FIELDS
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_gst = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class QuotationLowSideItem(models.Model):

    quotation_version = models.ForeignKey(
        QuotationVersion,
        related_name="low_side_items",
        on_delete=models.CASCADE
    )

    item = models.ForeignKey(
        item,
        on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default="NOS") 
    hsn_sac = models.CharField(max_length=50, null=True, blank=True)
    mathadi_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)

    # 🔥 NEW FIELDS
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_gst = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class ServiceCategory(models.Model):
    name = models.CharField(max_length=200)  # REFRIGERANT PIPING, CONTROL CABLING, etc.
    description = models.TextField(blank=True, null=True)
    sequence = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sequence', 'name']
        verbose_name_plural = "Service Categories"
    
    def __str__(self):
        return self.name

class ServiceSubCategory(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=200)  # between IDU to ODU, with Insulation, etc.
    description = models.TextField(blank=True, null=True)
    sequence = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sequence', 'name']
        verbose_name_plural = "Service Sub Categories"
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"

class ServiceMaster(models.Model):
    SERVICE_TYPES = [
        ('MATERIAL', 'Material Based'),
        ('LABOR', 'Labor Only'),
    ]
    
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    subcategory = models.ForeignKey(ServiceSubCategory, on_delete=models.CASCADE, related_name='services', null=True, blank=True)
    
    name = models.CharField(max_length=300)  # 12 HP ODU, Installation & Commissioning, etc.
    description = models.TextField(blank=True, null=True)
    service_type = models.CharField(max_length=10, choices=SERVICE_TYPES, default='LABOR')
    
    # For material-based services - Link to existing Item Master
    item = models.ForeignKey('product_management.item', on_delete=models.CASCADE, null=True, blank=True, 
                           help_text="Link to existing item from Item Master (for material-based services)")
    
    # Pricing
    unit = models.CharField(max_length=50)  # Mtr, Nos, Kg, Lot, etc.
    labor_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, 
                                   help_text="Labor cost per unit")
    
    # Settings
    sequence = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sequence', 'name']
    
    @property
    def material_rate(self):
        """Get material rate from linked item"""
        if self.item and self.service_type == 'MATERIAL':
            # You can customize this logic based on how you store rates in item model
            return getattr(self.item, 'rate', 0) or 0
        return 0
    
    @property
    def total_rate(self):
        """Calculate total rate (material + labor)"""
        return self.material_rate + self.labor_rate
    
    def __str__(self):
        return self.name

class QuotationServiceItem(models.Model):
    quotation_version = models.ForeignKey('QuotationVersion', on_delete=models.CASCADE, related_name='service_items')
    service = models.ForeignKey(ServiceMaster, on_delete=models.CASCADE)
    
    # Quantities and pricing
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    
    # Calculated amounts (same as high/low side items)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mathadi_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transportation_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_gst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Calculate amounts (same logic as high/low side items)
        self.base_amount = self.quantity * self.unit_price
        self.gst_amount = (self.base_amount * self.gst_percentage) / 100
        self.total_with_gst = self.base_amount + self.gst_amount + self.mathadi_charges + self.transportation_charges
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.service.name} - {self.quantity} {self.unit}"
