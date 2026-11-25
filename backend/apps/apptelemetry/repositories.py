"""Queries for the My Services telemetry tables (services.py orchestrates them)."""
from __future__ import annotations

from datetime import datetime

from django.db.models import F

from .models import AppFeedback, AppInstall, TelemetryRecord


class TelemetryRepository:
    @staticmethod
    def touch_install(app: str, install_id, now: datetime, **meta) -> AppInstall:
        """Get or create the install and record that it was seen now (non-empty meta wins)."""
        install, created = AppInstall.objects.get_or_create(
            app=app, install_id=install_id, defaults={'first_seen': now, 'last_seen': now, **meta},
        )
        if not created:
            changes = {'last_seen': now, **{k: v for k, v in meta.items() if v}}
            AppInstall.objects.filter(pk=install.pk).update(**changes)
            for key, value in changes.items():
                setattr(install, key, value)
        return install

    @staticmethod
    def existing_keys(install: AppInstall, sessions: set[int]) -> set[tuple]:
        """De-duplication keys already stored for these sessions of the install."""
        rows = TelemetryRecord.objects.filter(install=install, session__in=sessions).values_list(
            'session', 'type', 'direction', 'turn_id', 't',
        )
        return set(rows)

    @staticmethod
    def bulk_insert(records: list[TelemetryRecord]) -> None:
        # ignore_conflicts: a concurrent resend of the same batch must not raise.
        TelemetryRecord.objects.bulk_create(records, batch_size=500, ignore_conflicts=True)

    @staticmethod
    def add_turns(install: AppInstall, count: int) -> None:
        if count:
            AppInstall.objects.filter(pk=install.pk).update(turns_count=F('turns_count') + count)

    @staticmethod
    def find_install(app: str, install_id) -> AppInstall | None:
        return AppInstall.objects.filter(app=app, install_id=install_id).first()

    @staticmethod
    def create_feedback(**fields) -> AppFeedback:
        return AppFeedback.objects.create(**fields)

    @staticmethod
    def records(app: str, since: datetime, types: tuple[str, ...], fields: tuple[str, ...]):
        """Value rows of the app's records of `types` with client time >= since."""
        return TelemetryRecord.objects.filter(install__app=app, type__in=types, t__gte=since).values_list(*fields)

    @staticmethod
    def purge_records(before: datetime, chunk: int = 5000) -> int:
        """Delete raw records received before `before`, in chunks. Returns the number deleted."""
        deleted = 0
        while True:
            pks = list(TelemetryRecord.objects.filter(received_at__lt=before).values_list('pk', flat=True)[:chunk])
            if not pks:
                return deleted
            deleted += TelemetryRecord.objects.filter(pk__in=pks).delete()[0]
