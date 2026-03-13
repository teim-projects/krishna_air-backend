from django.db import models
from api.models import  BranchManagement, SiteManagement
from inventory.models import TermsConditions
# Create your models here.


class CompanyProfile(models.Model):

    name = models.CharField(max_length=255)
    address = models.TextField()

    gstin = models.CharField(max_length=50)
    pan = models.CharField(max_length=50)

    bank_name = models.CharField(max_length=255)
    account_no = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=50)
    branch = models.CharField(max_length=255)

    declaration = models.TextField(blank=True, null=True)


class Invoice(models.Model):

    GST_TYPE_CHOICES = (
        ("CGST_SGST", "CGST + SGST"),
        ("IGST", "IGST"),
        ("NO_GST", "No GST"),
    )

    invoice_no = models.CharField(max_length=50, unique=True)

    customer = models.ForeignKey(
        "lead_management.Customer",
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    invoice_date = models.DateField()

    terms_conditions = models.ManyToManyField(
        "inventory.TermsConditions",
        related_name="invoices",
        blank=True
    )

    # ===== BUYER SNAPSHOT =====
    buyer_name = models.CharField(max_length=255)
    buyer_address = models.TextField()
    buyer_gstin = models.CharField(max_length=50, blank=True, null=True)
    buyer_state = models.CharField(max_length=100, blank=True, null=True)
    buyer_state_code = models.CharField(max_length=10, blank=True, null=True)

    # ===== SHIP TO PARTY =====
    ship_to_address = models.TextField(blank=True, null=True)

    # ===== COMPANY SNAPSHOT =====
    
    
    # ===== BRANCH =====
    branch = models.ForeignKey(
        BranchManagement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )



    bank_name = models.CharField(max_length=255)
    account_no = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=50)
   

    declaration = models.TextField(blank=True, null=True)

    # ===== HEADER FIELDS FROM INVOICE =====
    # ===== HEADER FIELDS FROM INVOICE =====

    delivery_note = models.CharField(max_length=100, blank=True, null=True)
    delivery_note_date = models.DateField(blank=True, null=True, verbose_name="Delivery Note Date")
    supplier_ref = models.CharField(max_length=100, blank=True, null=True)
    other_references = models.CharField(max_length=255, blank=True, null=True)
    buyer_order_no = models.CharField(max_length=100, blank=True, null=True)
    buyer_dated = models.DateField(blank=True, null=True, verbose_name="Buyer Order Date")
    dispatch_doc_no = models.CharField(max_length=100, blank=True, null=True)
    dispatched_through = models.CharField(max_length=255, blank=True, null=True)
    destination = models.CharField(max_length=255, blank=True, null=True)
    # terms_of_payment = models.CharField(max_length=255, blank=True, null=True)
    # terms_of_delivery = models.TextField(blank=True, null=True)
    site = models.ForeignKey(
        SiteManagement,
        on_delete=models.PROTECT,
        related_name="invoices",
        null=True,
        blank=True
    )
    # ===== WORK DESCRIPTION =====
    work_description = models.TextField(blank=True, null=True)

    # ===== TAX TOTALS =====
    gst_type = models.CharField(max_length=20, choices=GST_TYPE_CHOICES,default="CGST_SGST")
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    taxable_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    amount_in_words = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)






class HighSideInvoiceItem(models.Model):

    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        related_name="high_side_items"
    )

    product_variant = models.ForeignKey(
        "product_management.ProductVariant",
        on_delete=models.CASCADE
    )

    description = models.TextField(blank=True, null=True)

    hsn_sac = models.CharField(max_length=50)

    gst_percent = models.DecimalField(max_digits=5, decimal_places=2)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    unit = models.CharField(max_length=20, default="NOS")

    rate = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self,*args,**kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args,**kwargs)


class LowSideInvoiceItem(models.Model):

    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        related_name="low_side_items"
    )

    item = models.ForeignKey(
        "product_management.item",
        on_delete=models.CASCADE
    )

    description = models.TextField(blank=True, null=True)

    gst_percent = models.DecimalField(max_digits=5, decimal_places=2)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    unit = models.CharField(max_length=20, default="NOS")

    rate = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self,*args,**kwargs):
        self.amount = self.quantity * self.rate
        super().save(*args,**kwargs)



