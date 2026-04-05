"""
Check CPU usage and send alert if any core exceeds threshold.

Designed to run every 5-15 minutes via cron/systemd timer.

Usage:
    python manage.py check_cpu_alert                  # default 75% threshold
    python manage.py check_cpu_alert --threshold 80   # custom threshold
"""
from django.core.management.base import BaseCommand

from core.services import SiteSettingsService
from interactions.notifications.telegram_api import TelegramBotAPI
from servermonitor.formatters import format_cpu_alert
from servermonitor.metrics import collect_cpu


class Command(BaseCommand):
    help = 'Check CPU cores and alert if above threshold'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold', type=float, default=75.0,
            help='CPU percent threshold for alert (default: 75)',
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        cpu = collect_cpu()

        alert_text = format_cpu_alert(cpu, threshold=threshold)
        if not alert_text:
            self.stdout.write(self.style.SUCCESS(
                f'All {cpu.core_count} cores below {threshold}% — no alert'
            ))
            return

        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            self.stderr.write(self.style.ERROR('telegram_owner_id not set'))
            return

        api = TelegramBotAPI()
        api.send_message(site.telegram_owner_id, alert_text)
        self.stdout.write(self.style.WARNING(f'CPU alert sent to {site.telegram_owner_id}'))
