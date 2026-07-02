from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from lead_management.models import Customer
from product_management.models import ProductVariant
from django.db import models
from api.models import CustomUser, BranchManagement
from product_management.models import item
from inventory.models import InventoryItem

class ServiceManagementRecord(models.Model):
    """Service Management Record for tracking AC maintenance and services"""
    
    SEGMENT_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
    ]
    
    CONTRACT_TYPE_CHOICES = [
        ('one_time', 'One Time'),
        ('amc', 'AMC'),
        ('warranty', 'Warranty'),
    ]
    
    CONTRACT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    AMC_SERVICE_TYPE_CHOICES = [
        ('COMPREHENSIVE', 'Comprehensive'),
        ('NON_COMPREHENSIVE', 'Non-Comprehensive'),
    ]
    
    # Customer Info
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='service_management_records'
    )
    customer_contact = models.CharField(max_length=15)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(null=True, blank=True)
    subject = models.CharField(max_length=500)
    
    # Contract Details
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        default='one_time'
    )
    contract_status = models.CharField(
        max_length=20,
        choices=CONTRACT_STATUS_CHOICES,
        default='active'
    )
    amc_service_type = models.CharField(
        max_length=20,
        choices=AMC_SERVICE_TYPE_CHOICES,
        blank=True,
        default=''
    )
    segment = models.CharField(
        max_length=20,
        choices=SEGMENT_CHOICES,
        default='residential'
    )
    service_start_date = models.DateField(null=True, blank=True)
    service_end_date = models.DateField(null=True, blank=True)
    
    # Location
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    address = models.TextField()
    
    # Pricing
    apply_gst = models.BooleanField(default=True)
    gst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00
    )
    total_price_without_gst = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    gst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_price_with_gst = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Meta
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        BranchManagement,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer_name} - {self.contract_type}"
    
    def calculate_totals(self):
        """Calculate GST and totals"""
        if self.apply_gst:
            self.gst_amount = (self.total_price_without_gst * self.gst_percentage) / 100
            self.total_price_with_gst = self.total_price_without_gst + self.gst_amount
        else:
            self.gst_amount = 0
            self.total_price_with_gst = self.total_price_without_gst


class ServiceManagementMaterial(models.Model):
    """Materials/AC Types selected for a Service Management Record"""
    
    service_record = models.ForeignKey(
        ServiceManagementRecord,
        on_delete=models.CASCADE,
        related_name='materials'
    )
    
    # AC Type (Product from low side)
    ac_type = models.ForeignKey(
        item,
        on_delete=models.PROTECT,
        related_name='service_records'
    )
    
    # Material/Service Details
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=50, default='Nos')
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    description = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        self.amount = (self.quantity or 0) * (self.rate or 0)
        super().save(*args, **kwargs)
        
        # Update parent record totals
        self.service_record.total_price_without_gst = sum(
            m.amount for m in self.service_record.materials.all()
        )
        self.service_record.calculate_totals()
        self.service_record.save()
    
    def __str__(self):
        return f"{self.service_record.customer_name} - {self.ac_type.item_code}"


class AMCContract(models.Model):
    """Customer's AMC Agreement"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]

    AMC_TYPE_CHOICES = [
        ('COMPREHENSIVE', 'Comprehensive'),
        ('NON_COMPREHENSIVE', 'Non-Comprehensive'),
    ]

    VISIT_FREQUENCY_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF_YEARLY', 'Half Yearly'),
        ('YEARLY', 'Yearly'),
    ]
    
    # Links
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='amc_contracts')
    amc_type = models.CharField(max_length=20, choices=AMC_TYPE_CHOICES, default='COMPREHENSIVE')
    visit_frequency = models.CharField(
        max_length=20,
        choices=VISIT_FREQUENCY_CHOICES,
        default='QUARTERLY'
    )
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    
    # Contract details
    contract_number = models.CharField(max_length=50, unique=True)
    
    # Dates
    sale_date = models.DateField()
    warranty_end_date = models.DateField()
    amc_start_date = models.DateField()
    amc_end_date = models.DateField()
    
    # Type logic
    amc_included_in_sale = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Cost tracking
    amc_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Renewal
    is_renewal = models.BooleanField(default=False)
    previous_contract = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.contract_number:
            prefix = f"AMC-{self.customer.id}"
            count = AMCContract.objects.filter(contract_number__startswith=prefix).count() + 1
            self.contract_number = f"{prefix}-{count:03d}"
        
        if self.amc_start_date < self.warranty_end_date and not self.amc_included_in_sale:
            self.amc_start_date = self.warranty_end_date + timedelta(days=1)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.contract_number} - {self.customer.name}"
    
    class Meta:
        ordering = ['-created_at']


class AMCSparePart(models.Model):
    """Spare parts used on non-comprehensive AMC contracts — deducts inventory stock."""
    amc_contract = models.ForeignKey(
        AMCContract,
        on_delete=models.CASCADE,
        related_name='spare_parts'
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='amc_spare_parts'
    )
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default='Nos')
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    hsn_sac = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    invoice = models.ForeignKey(
        'invoice.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='amc_spare_parts'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Spare part - {self.amc_contract.contract_number}"

    def _validate_low_side(self):
        if not self.inventory_item_id:
            return
        if self.inventory_item.product_variant_id is not None:
            raise ValidationError('Only low-side materials can be used as AMC spare parts.')
        if not self.inventory_item.item_id:
            raise ValidationError('Inventory item must be a low-side material.')

    def save(self, *args, **kwargs):
        self._validate_low_side()
        self.total_cost = (self.quantity_used or 0) * (self.rate_per_unit or 0)
        is_new = self.pk is None

        if is_new:
            with transaction.atomic():
                inv = InventoryItem.objects.select_for_update().get(id=self.inventory_item_id)
                if inv.quantity < self.quantity_used:
                    raise ValidationError(
                        f'Insufficient stock. Available: {inv.quantity}, Requested: {self.quantity_used}'
                    )
                InventoryItem.objects.filter(id=inv.id).update(
                    quantity=F('quantity') - self.quantity_used,
                    total_out_quantity=F('total_out_quantity') + self.quantity_used
                )
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            try:
                inv = InventoryItem.objects.select_for_update().get(id=self.inventory_item_id)
                InventoryItem.objects.filter(id=inv.id).update(
                    quantity=F('quantity') + self.quantity_used,
                    total_out_quantity=F('total_out_quantity') - self.quantity_used
                )
            except InventoryItem.DoesNotExist:
                pass
            super().delete(*args, **kwargs)


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
