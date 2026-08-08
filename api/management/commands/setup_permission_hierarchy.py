"""
Management command to set up the permission hierarchy.
Maps sub-modules to their parent modules.
"""

from django.core.management.base import BaseCommand
from api.models import RolePermission


class Command(BaseCommand):
    help = 'Set up permission hierarchy mapping sub-modules to parent modules'

    # Define parent-child relationships
    HIERARCHY_MAP = {
        # Inventory hierarchy
        'PO': 'Inventory',
        'GRN': 'Inventory',
        'Stock': 'Inventory',
        
        # Item Master hierarchy
        'HighSide': 'Item Master',
        'LowSide': 'Item Master',
        'Installation Work': 'Item Master',
        
        # AMC hierarchy
        'Service Management': 'AMC',
        
        # Accounts hierarchy
        'Work History': 'Accounts',
        'Completed Work': 'Accounts',
    }

    def handle(self, *args, **options):
        updated_count = 0
        
        for child_doc, parent_doc in self.HIERARCHY_MAP.items():
            updated = RolePermission.objects.filter(
                document_type=child_doc
            ).update(parent_document_type=parent_doc)
            
            if updated > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Set {child_doc} parent to {parent_doc} ({updated} records)'
                    )
                )
                updated_count += updated
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ No records found for {child_doc}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully updated {updated_count} permission records with hierarchy'
            )
        )
