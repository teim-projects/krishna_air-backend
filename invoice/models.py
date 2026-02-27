from django.db import models

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
    )

    invoice_no = models.CharField(max_length=50, unique=True)

    customer = models.ForeignKey(
        "lead_management.Customer",
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    invoice_date = models.DateField()

    # ===== BUYER SNAPSHOT =====
    buyer_name = models.CharField(max_length=255)
    buyer_address = models.TextField()
    buyer_gstin = models.CharField(max_length=50, blank=True, null=True)
    buyer_state = models.CharField(max_length=100, blank=True, null=True)
    buyer_state_code = models.CharField(max_length=10, blank=True, null=True)

    # ===== SHIP TO PARTY =====
    ship_to_address = models.TextField(blank=True, null=True)

    # ===== COMPANY SNAPSHOT =====
    company_name = models.CharField(max_length=255)
    company_address = models.TextField()
    company_gstin = models.CharField(max_length=50)
    company_pan = models.CharField(max_length=50)
    company_email = models.EmailField(blank=True, null=True)
    company_msme_number = models.CharField(max_length=100, blank=True, null=True)

    bank_name = models.CharField(max_length=255)
    account_no = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=50)
    branch = models.CharField(max_length=255)

    declaration = models.TextField(blank=True, null=True)

    # ===== HEADER FIELDS FROM INVOICE =====
    delivery_note = models.CharField(max_length=100, blank=True, null=True)
    supplier_ref = models.CharField(max_length=100, blank=True, null=True)
    buyer_order_no = models.CharField(max_length=100, blank=True, null=True)
    destination = models.CharField(max_length=255, blank=True, null=True)
    terms_of_delivery = models.TextField(blank=True, null=True)
    site_name = models.CharField(max_length=255, blank=True, null=True)

    # ===== WORK DESCRIPTION =====
    work_description = models.TextField(blank=True, null=True)

    # ===== TAX TOTALS =====
    gst_type = models.CharField(max_length=20, choices=GST_TYPE_CHOICES)

    taxable_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    amount_in_words = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)


class InvoiceItem(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        related_name="items",
        on_delete=models.CASCADE
    )

    # OPTIONAL LINKS
    product_variant = models.ForeignKey(
        "product_management.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    item = models.ForeignKey(
        "product_management.item",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # MANUAL DESCRIPTION
    description = models.TextField()

    hsn_sac = models.CharField(max_length=20)

    gst_percent = models.DecimalField(max_digits=5, decimal_places=2)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    unit = models.CharField(max_length=20, default="NOS")

    rate = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=12, decimal_places=2)



class InvoiceTaxBreakup(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        related_name="tax_breakups",
        on_delete=models.CASCADE
    )

    taxable_value = models.DecimalField(max_digits=12, decimal_places=2)

    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
