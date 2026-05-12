"""
Management command to regenerate all item codes using the shortcut fields.

Usage:
    python manage.py regenerate_item_codes

This command will:
1. Loop through all items in the database
2. Regenerate their item_code using the current shortcut fields
3. Handle duplicates by appending a number suffix
4. Update the database with the new codes
"""

from django.core.management.base import BaseCommand
from product_management.models import item


class Command(BaseCommand):
    help = 'Regenerate all item codes using shortcut fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        items = item.objects.all().select_related(
            'material_type_id',
            'item_type_id',
            'feature_type_id',
            'item_class_id',
            'brand'
        )
        
        total_items = items.count()
        updated_count = 0
        unchanged_count = 0
        
        self.stdout.write(f'Processing {total_items} items...\n')
        
        for idx, item_obj in enumerate(items, 1):
            old_code = item_obj.item_code
            
            # Generate new code
            base_code = item_obj.generate_item_code()
            
            # Handle duplicates
            new_code = base_code
            counter = 1
            
            # Check for duplicates (excluding current item)
            while item.objects.filter(item_code=new_code).exclude(pk=item_obj.pk).exists():
                new_code = f"{base_code}-{counter}"
                counter += 1
            
            if old_code != new_code:
                self.stdout.write(
                    f'{idx}/{total_items}: {self.style.WARNING(old_code)} → {self.style.SUCCESS(new_code)}'
                )
                
                if not dry_run:
                    item_obj.item_code = new_code
                    item_obj.save(update_fields=['item_code'])
                
                updated_count += 1
            else:
                unchanged_count += 1
                if options['verbosity'] >= 2:
                    self.stdout.write(f'{idx}/{total_items}: {old_code} (unchanged)')
        
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN COMPLETE'))
            self.stdout.write(f'Would update: {updated_count} items')
        else:
            self.stdout.write(self.style.SUCCESS(f'REGENERATION COMPLETE'))
            self.stdout.write(f'Updated: {updated_count} items')
        
        self.stdout.write(f'Unchanged: {unchanged_count} items')
        self.stdout.write(f'Total: {total_items} items')
        
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('Run without --dry-run to apply changes'))
