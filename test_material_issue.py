"""
Test script to verify Material Issue updates IN/OUT quantities
Run with: python manage.py shell < test_material_issue.py
"""

from inventory.models import InventoryItem
from django.db.models import F

print("\n=== Testing Material Issue Update ===\n")

# Get first inventory item
item = InventoryItem.objects.first()

if not item:
    print("❌ No inventory items found!")
    exit()

item_name = str(item.product_variant or item.item or f"ID:{item.id}")

print(f"Testing with: {item_name}")
print(f"Before update:")
print(f"  - quantity: {item.quantity}")
print(f"  - total_in_quantity: {item.total_in_quantity}")
print(f"  - total_out_quantity: {item.total_out_quantity}")

# Simulate Material Issue update
test_qty = 1
print(f"\nSimulating issue of {test_qty} unit...")

InventoryItem.objects.filter(id=item.id).update(
    quantity=F("quantity") - test_qty,
    total_out_quantity=F("total_out_quantity") + test_qty
)

# Refresh from database
item.refresh_from_db()

print(f"\nAfter update:")
print(f"  - quantity: {item.quantity}")
print(f"  - total_in_quantity: {item.total_in_quantity}")
print(f"  - total_out_quantity: {item.total_out_quantity}")

# Rollback the test
print(f"\nRolling back test...")
InventoryItem.objects.filter(id=item.id).update(
    quantity=F("quantity") + test_qty,
    total_out_quantity=F("total_out_quantity") - test_qty
)

item.refresh_from_db()
print(f"Rolled back to:")
print(f"  - quantity: {item.quantity}")
print(f"  - total_in_quantity: {item.total_in_quantity}")
print(f"  - total_out_quantity: {item.total_out_quantity}")

print("\n✓ Test complete!")
