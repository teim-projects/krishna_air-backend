from django.contrib import admin
from .models import ServiceCategory, ServiceSubCategory, ServiceMaster, QuotationServiceItem

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'sequence', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['sequence', 'name']

@admin.register(ServiceSubCategory)
class ServiceSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'sequence', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    ordering = ['category', 'sequence', 'name']

@admin.register(ServiceMaster)
class ServiceMasterAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'service_type', 'unit', 'get_total_rate', 'is_active']
    list_filter = ['category', 'service_type', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering = ['category', 'sequence', 'name']
    
    def get_total_rate(self, obj):
        return obj.total_rate
    get_total_rate.short_description = 'Total Rate'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'subcategory', 'service_type', 'sequence')
        }),
        ('Material Link (for Material-based services)', {
            'fields': ('items',),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('unit', 'labor_rate'),
            'description': 'Material rate will be auto-fetched from linked items'
        }),
        ('Settings', {
            'fields': ('is_active',)
        })
    )

@admin.register(QuotationServiceItem)
class QuotationServiceItemAdmin(admin.ModelAdmin):
    list_display = ['service', 'quotation_version', 'quantity', 'unit', 'unit_price', 'total_with_gst']
    list_filter = ['service__category', 'service__service_type', 'created_at']
    search_fields = ['service__name', 'quotation_version__quotation__quotation_no']
    readonly_fields = ['base_amount', 'gst_amount', 'total_with_gst']
