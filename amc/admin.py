from django.contrib import admin
from .models import AMCContract, AMCRenewal, TechnicianWorkRecord, AMCServiceVisit


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


@admin.register(TechnicianWorkRecord)
class TechnicianWorkRecordAdmin(admin.ModelAdmin):
    list_display = ['work_date', 'technician', 'customer_name', 'customer_phone', 'payment_amount']
    list_filter = ['work_date', 'technician']
    search_fields = ['customer_name', 'customer_phone', 'work_description']


@admin.register(AMCServiceVisit)
class AMCServiceVisitAdmin(admin.ModelAdmin):
    list_display = [
        'amc_contract',
        'visit_number',
        'planned_date',
        'amount',
        'status',
        'technician_work_record',
    ]
    list_filter = ['status', 'planned_date']
    search_fields = ['amc_contract__contract_number']
