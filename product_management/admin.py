from django.contrib import admin
from .models import *
# Register your models here.


admin.site.register(acType)
admin.site.register(acSubTypes)
admin.site.register(brand)
admin.site.register(ProductModel)
admin.site.register(ProductVariant)
admin.site.register(ProductInventory)