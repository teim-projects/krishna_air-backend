from django.contrib import admin
from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'mobile', 'state', 'supplier_category', 'is_active', 'created_at']
    list_filter = ['is_active', 'state', 'supplier_category', 'company_type', 'created_at']
    search_fields = ['name', 'email', 'mobile', 'gst_details', 'pan_details', 'office_poc_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'mobile', 'company_type', 'supplier_category')
        }),
        ('Address Details', {
            'fields': ('office_address', 'store_address', 'state', 'state_code')
        }),
        ('Contact Persons', {
            'fields': ('office_poc_name', 'office_poc_phone', 'store_poc_name', 'store_poc_phone')
        }),
        ('Legal & Financial', {
            'fields': ('gst_details', 'pan_details', 'bank_details')
        }),
        ('Other Details', {
            'fields': ('website', 'is_active', 'created_at', 'updated_at')
        }),
    )

