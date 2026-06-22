from django.contrib import admin
from .models import (
    AMCPackage, AMCContract, AMCService,
    AMCServiceParts, AMCServiceLabor, AMCInvoice, AMCRenewal
)


@admin.register(AMCPackage)
class AMCPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'package_type', 'annual_cost', 'service_visits_per_year', 'is_active']
    list_filter = ['package_type', 'is_active']
    search_fields = ['name']


@admin.register(AMCContract)
class AMCContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'customer', 'package', 'amc_start_date', 'amc_end_date', 'status']
    list_filter = ['status', 'amc_included_in_sale', 'created_at']
    search_fields = ['contract_number', 'customer__name']
    readonly_fields = ['contract_number']


@admin.register(AMCService)
class AMCServiceAdmin(admin.ModelAdmin):
    list_display = ['amc_contract', 'service_type', 'visit_date', 'status']
    list_filter = ['service_type', 'status', 'visit_date']
    search_fields = ['amc_contract__contract_number']


@admin.register(AMCServiceParts)
class AMCServicePartsAdmin(admin.ModelAdmin):
    list_display = ['service', 'inventory_item', 'quantity_used', 'total_cost']
    list_filter = ['include_in_customer_invoice']


@admin.register(AMCServiceLabor)
class AMCServiceLaborAdmin(admin.ModelAdmin):
    list_display = ['service', 'engineer_name', 'labor_hours', 'total_labor_cost']


@admin.register(AMCInvoice)
class AMCInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'service', 'total_amount', 'payment_status']
    list_filter = ['payment_status', 'invoice_date']
    search_fields = ['invoice_number']
    readonly_fields = ['invoice_number', 'subtotal', 'gst_amount', 'total_amount']


@admin.register(AMCRenewal)
class AMCRenewalAdmin(admin.ModelAdmin):
    list_display = ['previous_contract', 'renewal_date', 'status']
    list_filter = ['status']
