"""
Management command to auto-expire AMC contracts whose end date has passed.

Usage:
    python manage.py expire_amc_contracts
    python manage.py expire_amc_contracts --dry-run

Schedule (cron example - run daily at midnight):
    0 0 * * * cd /app && python manage.py expire_amc_contracts >> /var/log/amc_expiry.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from amc.models import AMCContract


class Command(BaseCommand):
    help = 'Auto-expire AMC contracts whose amc_end_date has passed today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which contracts would be expired without making changes',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE — No changes will be saved ===\n'))

        self.stdout.write(f'Running AMC expiry check for date: {today}\n')

        # Find all ACTIVE contracts whose end date has passed
        expired_qs = AMCContract.objects.filter(
            status='ACTIVE',
            amc_end_date__lt=today
        )

        count = expired_qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No contracts to expire. All contracts are up-to-date.'))
            return

        self.stdout.write(f'Found {count} contract(s) to expire:\n')

        expired = 0
        errors = 0

        for contract in expired_qs:
            try:
                self.stdout.write(
                    f'  → {contract.contract_number} | {contract.customer.name} | '
                    f'ended: {contract.amc_end_date}'
                )

                if not dry_run:
                    contract.status = 'EXPIRED'
                    contract.save(update_fields=['status'])
                    expired += 1
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Marked EXPIRED'))
                else:
                    self.stdout.write(self.style.WARNING(f'    [DRY RUN] Would mark EXPIRED'))

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'    ✗ Error: {str(e)}'))

        self.stdout.write('')
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'✓ Expired {expired} contract(s) successfully.'))
            if errors:
                self.stdout.write(self.style.ERROR(f'✗ {errors} error(s) occurred.'))
        else:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] {count} contract(s) would have been expired.'))

        self.stdout.write(self.style.SUCCESS('\nDone!'))
