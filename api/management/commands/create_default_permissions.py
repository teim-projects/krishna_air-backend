"""
Management command to create default permission records for all document types and roles.
This ensures that every role has permission entries for every document type.
"""

from django.core.management.base import BaseCommand
from api.models import RolePermission, Role


class Command(BaseCommand):
    help = 'Create default permission records for all roles and document types'

    # All document types in the system
    DOCUMENT_TYPES = [
        'Lead',
        'Customer',
        'Quotation',
        'Invoice',
        'Item Master',
        'Inventory',
        'PO',
        'GRN',
        'Stock',
        'HighSide',
        'LowSide',
        'Installation Work',
        'AMC',
        'Service Management',
        'Accounts',
        'Branch',
        'Site',
        'Role Permissions',
    ]

    # Default permissions for each role
    ROLE_DEFAULTS = {
        'admin': {
            'read_permission': True,
            'create_permission': True,
            'write_permission': True,
            'delete_permission': True,
            'import_permission': True,
            'export_permission': True,
            'view_all_permission': True,
            'modify_all_permission': True,
        },
        'sales': {
            'read_permission': True,
            'create_permission': True,
            'write_permission': True,
            'delete_permission': False,
            'import_permission': False,
            'export_permission': True,
            'view_all_permission': False,
            'modify_all_permission': False,
        },
        'technician': {
            'read_permission': True,
            'create_permission': True,
            'write_permission': True,
            'delete_permission': False,
            'import_permission': False,
            'export_permission': False,
            'view_all_permission': False,
            'modify_all_permission': False,
        },
    }

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0
        
        # Get all roles
        roles = Role.objects.all()
        
        if not roles.exists():
            self.stdout.write(self.style.WARNING('⚠ No roles found in database'))
            return
        
        # For each role
        for role in roles:
            role_name_lower = role.name.lower()
            
            # Get default permissions for this role type
            defaults = self.ROLE_DEFAULTS.get(role_name_lower, self.ROLE_DEFAULTS['sales'])
            
            # For each document type
            for doc_type in self.DOCUMENT_TYPES:
                # Check if permission already exists
                perm, created = RolePermission.objects.get_or_create(
                    role=role,
                    document_type=doc_type,
                    defaults=defaults
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Created: {doc_type} for {role.name}'
                        )
                    )
                else:
                    existing_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Created {created_count} new permission records'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'⚠ Found {existing_count} existing permission records'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal: {created_count + existing_count} permission records'
            )
        )
