"""
Cron health check — surfaces failed and overdue scheduled jobs.

Runs hourly. Inspects the last ``LOOKBACK_HOURS`` of `ops.CronRun` rows:

  - ``failed`` rows → grouped + Telegram alert
  - any ``ManagedCron`` whose schedule says it should have run but the
    last `CronRun` is older than 2× the expected interval → "overdue"

Designed to be quiet when everything is healthy: runs returning zero
failures + zero overdue produce no Telegram message.

Usage:
    python manage.py cron_health_check
    python manage.py cron_health_check --hours 6   # custom lookback
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.services import SiteSettingsService
from interactions.notifications.telegram_api import TelegramBotAPI
from ops.models import CronRun, CronStatus, ManagedCron
from servermonitor.formatters import format_cron_failure_alert


# Default lookback for failures.
LOOKBACK_HOURS = 1

# Per-cadence multiplier: a daily cron is "overdue" only after 2 days of
# silence, hourly after 2h, etc. Conservative — avoids noisy alerts when
# a cron just ran late.
OVERDUE_MULTIPLIER = 2


# Approximate interval lookup keyed by the cron-format string.
# We don't parse cron expressions here; we just match common shapes used
# in the ManagedCron seed migrations.
_SCHEDULE_INTERVAL = {
    '*/5 * * * *':  timedelta(minutes=5),
    '*/10 * * * *': timedelta(minutes=10),
    '*/15 * * * *': timedelta(minutes=15),
    '0 * * * *':    timedelta(hours=1),
    '0 */6 * * *':  timedelta(hours=6),
    '0 9 * * *':    timedelta(days=1),
    '0 4 * * 0':    timedelta(days=7),
}


def _expected_interval(schedule: str) -> timedelta | None:
    return _SCHEDULE_INTERVAL.get(schedule.strip())


class Command(BaseCommand):
    help = 'Surface failed + overdue scheduled jobs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=int, default=LOOKBACK_HOURS,
            help=f'Failure lookback window in hours (default: {LOOKBACK_HOURS}).',
        )
        parser.add_argument(
            '--no-alert', action='store_true',
            help='Compute report but do not send Telegram message.',
        )

    def handle(self, *args, **options):
        hours = max(options['hours'], 1)
        since = timezone.now() - timedelta(hours=hours)

        # ── Failures in lookback window ──
        failed_qs = (CronRun.objects
                     .filter(status=CronStatus.FAILED, started_at__gte=since)
                     .order_by('-started_at')
                     .values('command', 'started_at', 'duration_ms', 'error_summary'))
        failures = list(failed_qs)

        # ── Overdue managed crons ──
        overdue: list[dict] = []
        now = timezone.now()
        for mc in ManagedCron.objects.filter(enabled=True).only('command', 'schedule'):
            interval = _expected_interval(mc.schedule)
            if not interval:
                continue
            last_run = (CronRun.objects
                        .filter(command=mc.command)
                        .order_by('-started_at')
                        .only('started_at')
                        .first())
            last_seen = last_run.started_at if last_run else None
            if not last_seen or (now - last_seen) > interval * OVERDUE_MULTIPLIER:
                overdue.append({
                    'command': mc.command,
                    'schedule': mc.schedule,
                    'last_seen': last_seen,
                })

        text = format_cron_failure_alert(failures=failures, overdue=overdue)
        if text is None:
            self.stdout.write(self.style.SUCCESS(
                f'No cron failures in last {hours}h, no overdue jobs.'
            ))
            return

        if options['no_alert']:
            self.stdout.write(self.style.WARNING('Alert prepared (suppressed):'))
            self.stdout.write(text)
            return

        site = SiteSettingsService.get()
        if not site.telegram_owner_id:
            self.stderr.write(self.style.ERROR('telegram_owner_id not set — alert not sent'))
            self.stdout.write(text)
            return

        api = TelegramBotAPI()
        try:
            api.send_message(site.telegram_owner_id, text)
            self.stdout.write(self.style.WARNING(
                f'Alert sent — {len(failures)} failures, {len(overdue)} overdue'
            ))
        except Exception as e:  # noqa: BLE001
            self.stderr.write(self.style.ERROR(f'Telegram dispatch failed: {e}'))
            self.stdout.write(text)
