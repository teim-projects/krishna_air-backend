"""
Management command to fix inventory IN/OUT quantities
Run with: python manage.py fix_inventory_quantities
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, F
from inventory.models import InventoryItem, GRNProduct, MaterialIssueItem, MaterialReturnItem


class Command(BaseCommand):
    help = 'Recalculate and fix total_in_quantity and total_out_quantity for all inventory items'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting inventory quantity fix...'))
        
        fixed_count = 0
        error_count = 0
        
        for inventory in InventoryItem.objects.all():
            try:
                # Calculate total IN quantity from GRN
                grn_in = GRNProduct.objects.filter(
                    product_variant=inventory.product_variant,
                    item=inventory.item,
                    grn__is_completed=True
                ).aggregate(
                    total=Sum(F('received_quantity') - F('rejected_quantity'))
                )['total'] or 0
                
                # Calculate total IN quantity from Material Returns
                return_in = MaterialReturnItem.objects.filter(
                    material_issue_item__inventory_item=inventory,
                    material_return__is_completed=True
                ).aggregate(
                    total=Sum('quantity')
                )['total'] or 0
                
                # Calculate total OUT quantity from Material Issues
                issue_out = MaterialIssueItem.objects.filter(
                    inventory_item=inventory
                ).aggregate(
                    total=Sum('quantity')
                )['total'] or 0
                
                # Update the inventory item
                old_in = inventory.total_in_quantity
                old_out = inventory.total_out_quantity
                
                inventory.total_in_quantity = grn_in + return_in
                inventory.total_out_quantity = issue_out
                inventory.save(update_fields=['total_in_quantity', 'total_out_quantity'])
                
                fixed_count += 1
                
                # Get display name
                item_name = str(inventory.product_variant or inventory.item or f"ID:{inventory.id}")
                
                self.stdout.write(
                    f'✓ {item_name}: '
                    f'IN: {old_in} → {inventory.total_in_quantity}, '
                    f'OUT: {old_out} → {inventory.total_out_quantity}, '
                    f'Current: {inventory.quantity}'
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error fixing {inventory}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Fixed {fixed_count} inventory items'
            )
        )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'✗ {error_count} errors occurred')
            )
        
        self.stdout.write(self.style.SUCCESS('\nDone!'))
