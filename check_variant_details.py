import os
import django
import sys

sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "krishna_air.settings")
django.setup()

from product_management.models import ProductVariant

for pv in ProductVariant.objects.all():
    print(f"ID: {pv.id}, SKU: {pv.sku}, Capacity: {pv.capacity}, Unit: {pv.unit}, Star: {pv.star_rating}")
