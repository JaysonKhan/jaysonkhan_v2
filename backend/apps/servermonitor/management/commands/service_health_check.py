"""
Per-service health check.

Designed to run every 5 minutes via cron. For each unit in
``MONITORED_SERVICES``:

    1. Run `systemctl is-active`
    2. Compare to the previous ``ServiceCheckResult`` for the same unit
    3. Persist a new row (always — drives the daily report's restart count
       and the admin history view)
    4. If state flipped AND service is `critical=True` AND we haven't
       already alerted on this exact transition -> send a Telegram alert

Idempotent: re-running it back-to-back will not double-alert; the second
run sees the just-written row as the "previous" and reports no change.

Usage:
    python manage.py service_health_check
    python manage.py service_health_check --quiet   # don't print "all OK" line
    python manage.py service_health_check --no-alert  # collect only, skip TG
"""
from __future__ import annotations

from core.services import SiteSettingsService
from django.core.management.base import BaseCommand
from django.db.models import Max
from interactions.notifications.telegram_api import TelegramBotAPI
from servermonitor.formatters import format_service_alert
from servermonitor.metrics import MONITORED_SERVICES, collect_service_status
from servermonitor.models import ServiceCheckResult

# Status values where we couldn't actually reach systemctl. Treating
# these as "down" once caused an 11-service DOWN/UP storm when an admin
# "Run now" click ran the check from a gunicorn worker whose unit PATH
# was venv-only -- `systemctl` resolved nowhere, every unit returned
# this status, every unit "flipped". Skip alerting on these.
AMBIGUOUS_STATUSES = frozenset({'no-systemctl', 'unknown', 'error'})


class Command(BaseCommand):
    help = 'Check all services, persist results, alert on state changes.'

    def add_arguments(self, parser):
        parser.add_argument('--quiet', action='store_true',
                            help='Suppress the "no state changes" success line.')
        parser.add_argument('--no-alert', action='store_true',
                            help='Persist results but do not send Telegram alerts.')

    def handle(self, *args, **options):
        send_alerts = not options['no_alert']

        # Telegram setup -- best-effort. If owner_id missing we still record
        # results, just no alerts go out.
        api = None
        owner = None
        if send_alerts:
            site = SiteSettingsService.get()
            owner = site.telegram_owner_id
            if owner:
                api = TelegramBotAPI()

        changes: list[str] = []
        unchanged: list[str] = []
        errors: list[str] = []

        # Pre-fetch latest checked_at per unit (2 queries total, not N).
        units = [cfg['unit'] for cfg in MONITORED_SERVICES]
        latest_ts = {
            row['service_unit']: row['latest']
            for row in (
                ServiceCheckResult.objects
                .filter(service_unit__in=units)
                .values('service_unit')
                .annotate(latest=Max('checked_at'))
            )
        }
        prev_rows = {
            row.service_unit: row
            for row in ServiceCheckResult.objects.filter(
                service_unit__in=latest_ts.keys(),
                checked_at__in=latest_ts.values(),
            ).only('service_unit', 'is_active')
        } if latest_ts else {}

        for cfg in MONITORED_SERVICES:
            unit = cfg['unit']
            status = collect_service_status(
                unit,
                group=cfg['group'],
                display=cfg['display'],
                critical=cfg.get('critical', True),
            )

            prev = prev_rows.get(unit)
            prev_active = prev.is_active if prev else None
            is_first_check = prev is None
            ambiguous = status.status in AMBIGUOUS_STATUSES

            # If we couldn't actually probe systemctl, persist the previous
            # is_active rather than recording a synthetic "False" -- that
            # way the next real probe doesn't see a phantom transition,
            # and a future probe that's also ambiguous stays consistent
            # with whatever we last knew.
            recorded_active = (
                prev_active if (ambiguous and prev_active is not None) else status.active
            )
            is_change = (
                (not is_first_check)
                and (not ambiguous)
                and (prev_active != status.active)
            )

            row = ServiceCheckResult.objects.create(
                service_unit=unit,
                service_group=cfg['group'],
                service_display=cfg['display'],
                is_active=recorded_active,
                status_text=status.status,
                memory_mb=status.memory_mb,
                uptime_text=status.uptime or '',
                is_state_change=is_change,
                previous_active=prev_active,
            )

            if is_change and cfg.get('critical', True) and api and owner:
                text = format_service_alert(
                    unit=unit,
                    display=cfg['display'],
                    group=cfg['group'],
                    new_active=status.active,
                    previous_active=prev_active,
                    status_text=status.status,
                )
                try:
                    api.send_message(owner, text)
                    row.alert_sent = True
                    row.save(update_fields=['alert_sent'])
                    changes.append(unit)
                except Exception as e:  # noqa: BLE001
                    errors.append(f'{unit}: {e}')
            elif is_change:
                # Recorded the change but didn't alert (non-critical or no owner).
                changes.append(f'{unit} (silent)')
            else:
                unchanged.append(unit)

        if changes:
            self.stdout.write(self.style.WARNING(
                f'State changes ({len(changes)}): {", ".join(changes)}'
            ))
        elif not options['quiet']:
            self.stdout.write(self.style.SUCCESS(
                f'All {len(unchanged)} services unchanged.'
            ))

        if errors:
            for e in errors:
                self.stderr.write(self.style.ERROR(f'Alert dispatch failed: {e}'))
