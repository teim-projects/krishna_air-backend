"""Backfill planned AMC service visits for existing contracts."""
from django.core.management.base import BaseCommand

from amc.models import AMCContract
from amc.visit_service import sync_amc_service_visits


class Command(BaseCommand):
    help = 'Generate AMC service visit rows for all AMC contracts'

    def handle(self, *args, **options):
        count = 0
        for contract in AMCContract.objects.all().iterator():
            visits = sync_amc_service_visits(contract)
            count += len(visits)
        self.stdout.write(self.style.SUCCESS(f'Synced visits for contracts; {count} visit rows processed.'))
