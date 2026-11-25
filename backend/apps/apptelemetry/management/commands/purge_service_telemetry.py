"""Delete raw My Services telemetry records older than 180 days (contract retention).

Installs (with their lifetime turn counts) and feedback are kept. Runs daily from the managed
crontab block via `cron_run purge_service_telemetry`.
"""
from datetime import timedelta

from apptelemetry.models import TelemetryRecord
from apptelemetry.repositories import TelemetryRepository
from django.core.management.base import BaseCommand
from django.utils import timezone

RETENTION_DAYS = 180


class Command(BaseCommand):
    help = 'Delete raw telemetry records received more than 180 days ago (feedback is kept).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=RETENTION_DAYS)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        before = timezone.now() - timedelta(days=max(1, opts['days']))
        if opts['dry_run']:
            count = TelemetryRecord.objects.filter(received_at__lt=before).count()
            self.stdout.write(f'{count} records received before {before:%Y-%m-%d %H:%M} would be deleted.')
            return
        deleted = TelemetryRepository.purge_records(before)
        self.stdout.write(f'Deleted {deleted} records received before {before:%Y-%m-%d %H:%M}.')
