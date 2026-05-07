from django.contrib import admin
from .models import *
# Register your models here.


admin.site.register(acType)
admin.site.register(acSubTypes)
admin.site.register(brand)
admin.site.register(ProductModel)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['sku', 'get_pdf_display_name', 'capacity', 'unit', 'star_rating', 'mrp', 'is_active']
    list_filter = ['is_active', 'star_rating']
    search_fields = ['sku', 'product_model__model_no']
    
    def get_pdf_display_name(self, obj):
        """Show the PDF display name in admin list"""
        return obj.get_display_name_for_pdf()
    get_pdf_display_name.short_description = 'PDF Display Name'


admin.site.register(ProductInventory)