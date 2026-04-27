"""
Check CPU usage and send alert if any core exceeds threshold.

Designed to run every 5-15 minutes via cron/systemd timer.

Defaults updated 2026-04-27 after a flurry of false positives:
  - threshold raised 75 → 85 (75 still triggers the yellow visual badge,
    but only 85+ pages the operator)
  - measurement window extended 1s → 5s (sustained sample — Postgres
    parallel queries and gunicorn worker boots regularly spike a single
    1s window without representing real overload)

Usage:
    python manage.py check_cpu_alert                  # 85% / 5s sample
    python manage.py check_cpu_alert --threshold 90   # custom threshold
    python manage.py check_cpu_alert --interval 1     # tighter sample
"""
from django.core.management.base import BaseCommand

from core.services import SiteSettingsService
from interactions.notifications.telegram_api import TelegramBotAPI
from servermonitor.formatters import format_cpu_alert
from servermonitor.metrics import collect_cpu


class Command(BaseCommand):
    help = 'Check CPU cores and alert if above threshold (sustained 5s sample)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold', type=float, default=85.0,
            help='CPU percent threshold for alert (default: 85)',
        )
        parser.add_argument(
            '--interval', type=float, default=5.0,
            help='psutil sample window in seconds (default: 5 — sustained)',
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        interval = options['interval']
        cpu = collect_cpu(interval=interval)

        alert_text = format_cpu_alert(cpu, threshold=threshold)
        if not alert_text:
            self.stdout.write(self.style.SUCCESS(
                f'All {cpu.core_count} cores below {threshold}% '
                f'(sampled over {interval}s) — no alert'
            ))
            return

        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            self.stderr.write(self.style.ERROR('telegram_owner_id not set'))
            return

        api = TelegramBotAPI()
        api.send_message(site.telegram_owner_id, alert_text)
        self.stdout.write(self.style.WARNING(f'CPU alert sent to {site.telegram_owner_id}'))
