from django.db import models
from api.models import SiteManagement, BranchManagement
from product_management.models import ProductVariant, item
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

class Vendor(models.Model):
    # Required fields
    name = models.CharField(max_length=200)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    office_address = models.TextField()
    gst_details = models.CharField(max_length=15)
    office_poc_name = models.CharField(max_length=100, blank=True, null=True)
    office_poc_phone = models.CharField(max_length=15, blank=True, null=True)
    
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
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="purchase_orders"
    )

    site = models.ForeignKey(
        SiteManagement,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        null=True,
        blank=True
    )

    branch = models.ForeignKey(
        BranchManagement,
        on_delete=models.PROTECT,
        related_name="purchase_orders"
    )

    terms_conditions = models.ManyToManyField(
        TermsConditions,
        related_name="purchase_orders",
        blank=True
    )

    po_date = models.DateField(null=True, blank=True)

    book_no = models.CharField(max_length=10)
    purchase_order_no = models.CharField(max_length=50, blank=True)

    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)

    quotation_ref_no = models.CharField(max_length=50, blank=True, null=True)
    quotation_date = models.DateField(null=True, blank=True)

    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_no = models.CharField(max_length=20, blank=True, null=True)

    # Financial Fields
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18)

    gst_type = models.CharField(
        max_length=20,
        choices=[
            ("inclusive", "Inclusive"),
            ("exclusive", "Exclusive")
        ],
        default="exclusive"
    )

    transport_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    round_off = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(-1000),
            MaxValueValidator(1000)
        ]
    )
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("purchase_order_no", "version")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Auto-generate PO Number
        if is_new and not self.purchase_order_no:
            now = timezone.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            padded_id = str(self.id).zfill(4)
            self.purchase_order_no = f"{self.book_no}/{year}/{month}{padded_id}"
            super().save(update_fields=["purchase_order_no"])

    def calculate_totals(self):
        products = self.products.filter(is_section=False)

        subtotal = sum([p.amount for p in products], Decimal("0.00"))
        self.subtotal = subtotal

        if self.gst_type == "exclusive":
            gst_amount = (subtotal * self.gst_percentage) / Decimal("100")
            total = subtotal + gst_amount
        else:
            # Inclusive GST
            gst_amount = (subtotal * self.gst_percentage) / (
                Decimal("100") + self.gst_percentage
            )
            total = subtotal

        total += self.transport_charges
        total += self.round_off

        self.grand_total = total
        self.save(update_fields=["subtotal", "grand_total"])

    def __str__(self):
        return f"{self.purchase_order_no} (v{self.version})" 

class PurchaseOrderProduct(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="products"
    )

    # Product references
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    item = models.ForeignKey(
        item,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    # Section + Hierarchy
    serial_no = models.CharField(max_length=10, blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=1)

    is_section = models.BooleanField(default=False)
    section_title = models.CharField(max_length=255, blank=True, null=True)

    # Product Data
    description = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    uom = models.CharField(max_length=20, blank=True, null=True)

    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)

    class Meta:
        ordering = ["sort_order"]

    def clean(self):
        if not self.is_section:
            if not self.product_variant and not self.item:
                raise ValidationError("Either product_variant or item is required.")
            if self.product_variant and self.item:
                raise ValidationError("Select only one: product_variant or item.")

    def save(self, *args, **kwargs):
        if self.is_section:
            self.amount = Decimal("0.00")
            self.quantity = Decimal("0.00")
            self.rate = Decimal("0.00")
        else:
            self.amount = (self.quantity or Decimal("0.00")) * (
                self.rate or Decimal("0.00")
            )

        super().save(*args, **kwargs)


