"""
Management command to set NULL quantities to 0
Run with: python manage.py set_null_quantities_to_zero
"""

from django.core.management.base import BaseCommand
from inventory.models import InventoryItem


class Command(BaseCommand):
    help = 'Set NULL total_in_quantity and total_out_quantity to 0'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Setting NULL quantities to 0...'))
        
        # Update NULL values to 0
        updated_in = InventoryItem.objects.filter(total_in_quantity__isnull=True).update(total_in_quantity=0)
        updated_out = InventoryItem.objects.filter(total_out_quantity__isnull=True).update(total_out_quantity=0)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Updated {updated_in} items with NULL total_in_quantity to 0'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Updated {updated_out} items with NULL total_out_quantity to 0'
            )
        )
        
        # Show current state
        self.stdout.write(self.style.WARNING('\nCurrent inventory state:'))
        for item in InventoryItem.objects.all()[:10]:
            item_name = str(item.product_variant or item.item or f"ID:{item.id}")
            self.stdout.write(
                f'  {item_name}: '
                f'IN={item.total_in_quantity}, '
                f'OUT={item.total_out_quantity}, '
                f'Current={item.quantity}'
            )
        
        total_items = InventoryItem.objects.count()
        if total_items > 10:
            self.stdout.write(f'  ... and {total_items - 10} more items')
        
        self.stdout.write(self.style.SUCCESS('\nDone!'))
