"""
Management command: send daily server health report to Telegram owner.

Usage:
    python manage.py server_health_report          # full daily report
    python manage.py server_health_report --quick   # quick status only
    python manage.py server_health_report --tariff  # include tariff advice

Cron (systemd timer or crontab):
    0 9 * * * /path/to/venv/bin/python /path/to/manage.py server_health_report
"""
from django.core.management.base import BaseCommand

from core.services import SiteSettingsService
from interactions.notifications.telegram_api import TelegramBotAPI
from servermonitor.contabo import analyze_tariff, format_tariff_advice
from servermonitor.formatters import (
    format_cpu_alert,
    format_full_report,
    format_status_report,
)
from servermonitor.metrics import collect_cpu, collect_disk, collect_full_snapshot, collect_memory


class Command(BaseCommand):
    help = 'Send server health report to Telegram owner'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quick', action='store_true',
            help='Send quick status instead of full report',
        )
        parser.add_argument(
            '--tariff', action='store_true',
            help='Include Contabo tariff advice',
        )
        parser.add_argument(
            '--alert-only', action='store_true',
            help='Only send if there are warnings/alerts',
        )

    def handle(self, *args, **options):
        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            self.stderr.write(self.style.ERROR('telegram_owner_id not set in SiteSettings'))
            return

        api = TelegramBotAPI()
        tg_id = site.telegram_owner_id

        self.stdout.write('Collecting server metrics...')
        snapshot = collect_full_snapshot()

        # Check for alerts
        cpu_alert = format_cpu_alert(snapshot.cpu, threshold=75.0)
        has_alerts = cpu_alert is not None
        has_service_down = any(not s.active for s in snapshot.services)

        if options['alert_only'] and not has_alerts and not has_service_down:
            self.stdout.write(self.style.SUCCESS('No alerts — skipping report'))
            return

        # Build report
        if options['quick']:
            text = format_status_report(snapshot)
        else:
            text = format_full_report(snapshot)

        # Append CPU alert
        if cpu_alert:
            text += '\n\n' + cpu_alert

        # Append service down warning
        if has_service_down:
            down = [s.name for s in snapshot.services if not s.active]
            text += f'\n\n🚨 <b>Down services:</b> {", ".join(down)}'

        api.send_message(tg_id, text)
        self.stdout.write(self.style.SUCCESS(f'Report sent to {tg_id}'))

        # Tariff advice (separate message)
        if options['tariff']:
            cpu = snapshot.cpu
            mem = snapshot.memory
            disk = snapshot.disk
            advice = analyze_tariff(cpu, mem, disk)
            tariff_text = format_tariff_advice(advice)
            api.send_message(tg_id, tariff_text)
            self.stdout.write(self.style.SUCCESS('Tariff advice sent'))
