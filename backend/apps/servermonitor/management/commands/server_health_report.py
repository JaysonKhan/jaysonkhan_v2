"""
Management command: send daily server health report to Telegram owner.

Usage:
    python manage.py server_health_report          # full daily report
    python manage.py server_health_report --quick   # quick status only
    python manage.py server_health_report --tariff  # include tariff advice
    python manage.py server_health_report --alert-only  # send only on issues

Cron (systemd timer or crontab):
    0 9 * * * /path/to/venv/bin/python /path/to/manage.py server_health_report

The full report now also folds in:
  - Per-service restart count over the last 24h (from ServiceCheckResult)
  - Cron summary over the last 24h (success/fail counts + overdue list)

If you ever want a strictly "infra only" snapshot, the --quick flag
still produces the compact CPU+RAM+disk+services view without history.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta

from core.services import SiteSettingsService
from django.core.management.base import BaseCommand
from django.utils import timezone
from interactions.notifications.telegram_api import TelegramBotAPI
from ops.models import CronRun, CronStatus, ManagedCron
from servermonitor.contabo import analyze_tariff, format_tariff_advice
from servermonitor.formatters import (
    format_cpu_alert,
    format_full_report,
    format_status_report,
)
from servermonitor.metrics import collect_full_snapshot
from servermonitor.models import ServiceCheckResult

from .cron_health_check import _expected_interval

REPORT_WINDOW = timedelta(hours=24)
# Retention for the raw per-check history. The 2-min health check writes
# 11 rows/run (~240k rows at 30 days); restart counts only look back 24h,
# so 30 days is ample history for the admin view. Daily report = janitor.
PRUNE_AFTER = timedelta(days=30)


def _prune_old_results() -> int:
    """Delete ServiceCheckResult rows older than the retention window."""
    cutoff = timezone.now() - PRUNE_AFTER
    deleted, _ = ServiceCheckResult.objects.filter(checked_at__lt=cutoff).delete()
    return deleted


def _restart_counts_24h() -> dict[str, int]:
    """Count active→inactive transitions per service in the last 24h.

    A "restart" is any state-change check where the service ended up
    INACTIVE (the recovery transition is then the recovery, not a restart).
    """
    since = timezone.now() - REPORT_WINDOW
    qs = (ServiceCheckResult.objects
          .filter(checked_at__gte=since, is_state_change=True, is_active=False)
          .values_list('service_unit', flat=True))
    return dict(Counter(qs))


def _cron_summary_24h() -> dict:
    """Aggregate CronRun stats for the last 24 hours."""
    since = timezone.now() - REPORT_WINDOW
    base = CronRun.objects.filter(started_at__gte=since)
    success = base.filter(status=CronStatus.SUCCESS).count()
    failed = base.filter(status=CronStatus.FAILED).count()
    recent_failures = list(
        base.filter(status=CronStatus.FAILED)
            .order_by('-started_at')
            .values('command', 'started_at', 'error_summary')[:5]
    )

    # Overdue managed crons — last run > 24h ago.
    overdue = []
    now = timezone.now()
    for mc in ManagedCron.objects.filter(enabled=True).only('command', 'schedule'):
        last = (CronRun.objects.filter(command=mc.command)
                .order_by('-started_at').only('started_at').first())
        last_seen = last.started_at if last else None
        interval = _expected_interval(mc.schedule)
        threshold = (interval * 2) if interval else REPORT_WINDOW
        if not last_seen or (now - last_seen) > threshold:
            overdue.append({'command': mc.command, 'last_seen': last_seen})

    return {
        'success': success,
        'failed': failed,
        'recent_failures': recent_failures,
        'overdue': overdue,
    }


class Command(BaseCommand):
    help = 'Send server health report to Telegram owner.'

    def add_arguments(self, parser):
        parser.add_argument('--quick', action='store_true',
                            help='Send compact status instead of full report.')
        parser.add_argument('--tariff', action='store_true',
                            help='Include Contabo tariff advice as separate message.')
        parser.add_argument('--alert-only', action='store_true',
                            help='Only send if there are warnings/alerts.')

    def handle(self, *args, **options):
        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            self.stderr.write(self.style.ERROR('telegram_owner_id not set in SiteSettings'))
            return

        api = TelegramBotAPI()
        tg_id = site.telegram_owner_id

        # Janitor: keep the per-check history bounded (runs daily, before the
        # alert-only early return, so it always fires).
        pruned = _prune_old_results()
        if pruned:
            self.stdout.write(f'Pruned {pruned} old ServiceCheckResult rows (>{PRUNE_AFTER.days}d)')

        self.stdout.write('Collecting server metrics...')
        snapshot = collect_full_snapshot(cpu_interval=5.0)

        cpu_alert = format_cpu_alert(snapshot.cpu, threshold=85.0)
        has_cpu_alert = cpu_alert is not None
        has_service_down = any(not s.active for s in snapshot.services)

        # Pull supplementary data only for the full report (not quick).
        restart_counts: dict[str, int] = {}
        cron_summary: dict | None = None
        if not options['quick']:
            restart_counts = _restart_counts_24h()
            cron_summary = _cron_summary_24h()

        cron_unhealthy = bool(cron_summary and (cron_summary['failed'] or cron_summary['overdue']))

        if options['alert_only'] and not (has_cpu_alert or has_service_down or cron_unhealthy):
            self.stdout.write(self.style.SUCCESS('No alerts — skipping report'))
            return

        if options['quick']:
            text = format_status_report(snapshot)
        else:
            text = format_full_report(
                snapshot,
                restart_counts=restart_counts,
                cron_summary=cron_summary,
            )

        if cpu_alert:
            text += '\n\n' + cpu_alert

        if has_service_down:
            down = [(s.display or s.name) for s in snapshot.services if not s.active]
            text += f'\n\n🚨 <b>Down services:</b> {", ".join(down)}'

        api.send_message(tg_id, text)
        self.stdout.write(self.style.SUCCESS(f'Report sent to {tg_id}'))

        if options['tariff']:
            advice = analyze_tariff(snapshot.cpu, snapshot.memory, snapshot.disk)
            api.send_message(tg_id, format_tariff_advice(advice))
            self.stdout.write(self.style.SUCCESS('Tariff advice sent'))
