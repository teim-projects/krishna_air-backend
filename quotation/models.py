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

    subject = models.CharField(max_length=255)
    site_name = models.CharField(max_length=255, blank=True, null=True)
    thank_you_note = models.TextField(blank=True, null=True)

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

    mathadi_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transportation_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)

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

    mathadi_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # 🔥 NEW FIELDS
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_gst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
