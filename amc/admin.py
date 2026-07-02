from django.contrib import admin
from .models import AMCContract, AMCRenewal


@admin.register(AMCContract)
class AMCContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'customer', 'amc_type', 'amc_start_date', 'amc_end_date', 'status']
    list_filter = ['status', 'amc_included_in_sale', 'amc_type', 'created_at']
    search_fields = ['contract_number', 'customer__name', 'amc_type']
    readonly_fields = ['contract_number']


@admin.register(AMCRenewal)
class AMCRenewalAdmin(admin.ModelAdmin):
    list_display = ['previous_contract', 'renewal_date', 'status']
    list_filter = ['status']
