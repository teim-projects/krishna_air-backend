from django.contrib import admin
from .models import ServiceMaster, QuotationServiceItem

@admin.register(ServiceMaster)
class ServiceMasterAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'service_type', 'unit', 'labor_rate', 'is_active']
    list_filter = ['service_type', 'is_active']
    search_fields = ['name', 'category', 'subcategory']
    ordering = ['category', 'sequence', 'name']

@admin.register(QuotationServiceItem)
class QuotationServiceItemAdmin(admin.ModelAdmin):
    list_display = ['service', 'quotation_version', 'quantity', 'unit', 'unit_price', 'total_with_gst']
    list_filter = ['service__service_type', 'created_at']
    search_fields = ['service__name', 'quotation_version__quotation__quotation_no']
    readonly_fields = ['base_amount', 'gst_amount', 'total_with_gst']