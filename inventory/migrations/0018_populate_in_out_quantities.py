# Data migration to populate total_in_quantity and total_out_quantity

from django.db import migrations
from django.db.models import Sum, F


def populate_in_out_quantities(apps, schema_editor):
    """
    Calculate and populate total_in_quantity and total_out_quantity
    for existing inventory items based on GRN and Material Issue history
    """
    InventoryItem = apps.get_model('inventory', 'InventoryItem')
    GRNProduct = apps.get_model('inventory', 'GRNProduct')
    MaterialIssueItem = apps.get_model('inventory', 'MaterialIssueItem')
    MaterialReturnItem = apps.get_model('inventory', 'MaterialReturnItem')
    
    for inventory in InventoryItem.objects.all():
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
        inventory.total_in_quantity = grn_in + return_in
        inventory.total_out_quantity = issue_out
        inventory.save(update_fields=['total_in_quantity', 'total_out_quantity'])


def reverse_populate(apps, schema_editor):
    """
    Reset total_in_quantity and total_out_quantity to 0
    """
    InventoryItem = apps.get_model('inventory', 'InventoryItem')
    InventoryItem.objects.all().update(
        total_in_quantity=0,
        total_out_quantity=0
    )


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0017_inventoryitem_total_in_quantity_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_in_out_quantities, reverse_populate),
    ]
