from django.db import models
from django.utils import timezone
from datetime import timedelta
from lead_management.models import Customer
from product_management.models import ProductVariant

class AMCPackage(models.Model):
    """Different AMC package types"""
    COMPREHENSIVE = 'COMPREHENSIVE'
    NON_COMPREHENSIVE = 'NON_COMPREHENSIVE'
    
    PACKAGE_TYPES = [
        (COMPREHENSIVE, 'Comprehensive Service'),
        (NON_COMPREHENSIVE, 'Non-Comprehensive Service'),
    ]
    
    name = models.CharField(max_length=100)  # e.g., "Gold", "Platinum"
    package_type = models.CharField(max_length=50, choices=PACKAGE_TYPES)
    description = models.TextField(blank=True, null=True)
    
    # Pricing
    annual_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Service details
    service_visits_per_year = models.IntegerField(default=4)  # Quarterly, half-yearly, etc.
    parts_replacement_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # For non-comprehensive
    response_time_hours = models.IntegerField(default=24)  # How quickly engineer responds
    includes_emergency_calls = models.BooleanField(default=True)
    emergency_call_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # For non-comprehensive
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_package_type_display()})"
    
    class Meta:
        ordering = ['name']


class AMCContract(models.Model):
    """Customer's AMC Agreement"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Links
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='amc_contracts')
    package = models.ForeignKey(AMCPackage, on_delete=models.PROTECT)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)  # Which AC model
    
    # Contract details
    contract_number = models.CharField(max_length=50, unique=True)
    
    # Dates
    sale_date = models.DateField()  # When AC was sold/installed
    warranty_end_date = models.DateField()  # Standard 1-year warranty
    amc_start_date = models.DateField()  # When AMC starts (after warranty or immediately)
    amc_end_date = models.DateField()  # When AMC ends
    
    # Type logic
    amc_included_in_sale = models.BooleanField(default=False)  # True = AMC included in sale price, False = Separate purchase
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Cost tracking
    amc_cost = models.DecimalField(max_digits=10, decimal_places=2)  # What customer paid for this AMC
    
    # Renewal
    is_renewal = models.BooleanField(default=False)  # Is this a renewal of previous AMC?
    previous_contract = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-generate contract number if not set
        if not self.contract_number:
            prefix = f"AMC-{self.customer.id}"
            count = AMCContract.objects.filter(contract_number__startswith=prefix).count() + 1
            self.contract_number = f"{prefix}-{count:03d}"
        
        # Validate dates
        if self.amc_start_date < self.warranty_end_date and not self.amc_included_in_sale:
            self.amc_start_date = self.warranty_end_date + timedelta(days=1)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.contract_number} - {self.customer.name}"
    
    class Meta:
        ordering = ['-created_at']


class AMCService(models.Model):
    """Individual service visit under AMC"""
    SERVICE_TYPES = [
        ('SCHEDULED', 'Scheduled Maintenance'),
        ('EMERGENCY', 'Emergency Repair'),
        ('FOLLOW_UP', 'Follow-up Visit'),
    ]
    
    amc_contract = models.ForeignKey(AMCContract, on_delete=models.CASCADE, related_name='services')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    
    # Visit details
    visit_date = models.DateField()
    engineer_assigned = models.CharField(max_length=100, blank=True, null=True)
    
    # Description
    issue_reported = models.TextField(blank=True, null=True)  # What customer complained about
    work_performed = models.TextField(blank=True, null=True)  # What engineer did
    
    # For non-comprehensive: This determines if customer invoice is generated
    is_billable = models.BooleanField(default=False)  # True = Generate customer invoice (non-comprehensive only)
    
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('PENDING_PARTS', 'Pending Parts'),
    ], default='SCHEDULED')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Service - {self.amc_contract.contract_number} - {self.visit_date}"
    
    class Meta:
        ordering = ['-visit_date']


class AMCServiceParts(models.Model):
    """Parts used in each service visit"""
    service = models.ForeignKey(AMCService, on_delete=models.CASCADE, related_name='parts_used')
    inventory_item = models.ForeignKey('inventory.InventoryItem', on_delete=models.PROTECT)
    
    quantity_used = models.PositiveIntegerField(default=1)
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)  # quantity * rate
    
    # For non-comprehensive: Include in customer invoice?
    include_in_customer_invoice = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Auto-calculate total cost
        self.total_cost = self.quantity_used * self.rate_per_unit
        
        # Reduce inventory for both comprehensive and non-comprehensive
        self.inventory_item.quantity -= self.quantity_used
        self.inventory_item.total_out_quantity += self.quantity_used
        self.inventory_item.save()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        item_name = self.inventory_item.product_variant.sku if self.inventory_item.product_variant else self.inventory_item.item.item_code
        return f"Parts - {item_name} - {self.quantity_used} units"


class AMCServiceLabor(models.Model):
    """Labor charges for service visit (mainly for non-comprehensive)"""
    service = models.OneToOneField(AMCService, on_delete=models.CASCADE, related_name='labor')
    
    engineer_name = models.CharField(max_length=100)
    labor_hours = models.DecimalField(max_digits=5, decimal_places=2)
    rate_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    total_labor_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    # For non-comprehensive: Include in customer invoice?
    include_in_customer_invoice = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        self.total_labor_cost = self.labor_hours * self.rate_per_hour
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Labor - {self.engineer_name} - {self.labor_hours} hrs"


class AMCInvoice(models.Model):
    """Customer invoice for non-comprehensive services only"""
    service = models.OneToOneField(AMCService, on_delete=models.CASCADE, related_name='customer_invoice')
    
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(auto_now_add=True)
    
    # Costs
    parts_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Travel, etc.
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment
    payment_status = models.CharField(max_length=20, choices=[
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partial Payment'),
        ('PAID', 'Paid'),
    ], default='UNPAID')
    
    def save(self, *args, **kwargs):
        # Auto-generate invoice number
        if not self.invoice_number:
            prefix = f"AMC-INV-{self.service.amc_contract.customer.id}"
            count = AMCInvoice.objects.filter(invoice_number__startswith=prefix).count() + 1
            self.invoice_number = f"{prefix}-{count:03d}"
        
        # Calculate totals
        self.subtotal = self.parts_total + self.labor_total + self.other_charges
        self.gst_amount = (self.subtotal * self.gst_percent) / 100
        self.total_amount = self.subtotal + self.gst_amount
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.invoice_number}"
    
    class Meta:
        ordering = ['-invoice_date']


class AMCRenewal(models.Model):
    """Track renewals and manage expiry"""
    previous_contract = models.OneToOneField(AMCContract, on_delete=models.CASCADE, related_name='renewal')
    new_contract = models.OneToOneField(
        AMCContract, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='renewed_from'
    )
    
    renewal_date = models.DateField()
    renewal_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('RENEWED', 'Renewed'),
        ('EXPIRED', 'Expired'),
    ], default='PENDING')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Renewal - {self.previous_contract.contract_number}"
