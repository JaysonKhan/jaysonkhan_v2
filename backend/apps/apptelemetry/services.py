"""My Services: store telemetry batches and feedback, and compute the aggregates.

Public figures (`public_stats`) are aggregates only; a breakdown row is shown only when at least
`MIN_INSTALLS` installs contributed to it. Feedback text and per-install data stay owner-only
(`owner_stats`, admin).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Max, Sum
from django.utils import timezone

from .models import AppFeedback, AppInstall, TelemetryRecord
from .repositories import TelemetryRepository
from .validation import DEFAULT_MY_LANG, parse_record

MIN_INSTALLS = 5
WINDOW_DAYS = 30
PUBLIC_CACHE_SECONDS = 300
T = TelemetryRecord.Type


def percentile(values: list[int], p: float) -> float | None:
    """Linear-interpolation percentile (same as PostgreSQL percentile_cont / numpy default)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p / 100
    low, high = math.floor(rank), math.ceil(rank)
    if low == high:
        return float(ordered[low])
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _latency(values: list[int]) -> dict:
    p50, p95 = percentile(values, 50), percentile(values, 95)
    return {
        'turns': len(values),
        'p50': round(p50) if p50 is not None else None,
        'p95': round(p95) if p95 is not None else None,
    }


# ── ingestion ───────────────────────────────────────────────────────────────

def _dedup_key(fields: dict) -> tuple:
    """The contract's de-duplication key within one install: (session, type, direction, turnId, t)."""
    return fields['session'], fields['type'], fields.get('direction', ''), fields['turn_id'], fields['t']


class TelemetryService:
    def __init__(self, repository: TelemetryRepository | None = None):
        self.repository = repository or TelemetryRepository()

    def ingest(self, envelope: dict, now: datetime | None = None) -> tuple[int, int]:
        """Store a validated envelope's records. Returns (accepted, ignored)."""
        now = now or timezone.now()
        parsed, ignored, seen = [], 0, set()
        for raw in envelope['records']:
            fields = parse_record(raw, now)
            key = fields and _dedup_key(fields)
            if fields is None or key in seen:
                ignored += 1
                continue
            seen.add(key)
            parsed.append(fields)

        with transaction.atomic():
            install = self.repository.touch_install(
                envelope['app'], envelope['install_id'], now,
                app_version=envelope['app_version'],
                os_version=envelope['os_version'],
                ui_language=envelope['ui_language'],
            )
            existing = self.repository.existing_keys(install, {f['session'] for f in parsed}) if parsed else set()
            new = [f for f in parsed if _dedup_key(f) not in existing]
            ignored += len(parsed) - len(new)
            self.repository.bulk_insert([
                TelemetryRecord(install=install, received_at=now, app_version=envelope['app_version'], **f)
                for f in new
            ])
            self.repository.add_turns(install, sum(1 for f in new if f['type'] == T.TURN))
        return len(new), ignored

    def create_feedback(self, fields: dict) -> AppFeedback:
        install_id = fields.pop('install_id')
        install = self.repository.find_install(fields['app'], install_id) if install_id else None
        feedback = self.repository.create_feedback(install=install, **fields)
        _notify_owner(feedback)
        return feedback


def _notify_owner(feedback: AppFeedback) -> None:
    """Telegram note to the owner's admin group (no e-mail in it). Never blocks the request."""
    from interactions.notifications.service import NotificationService, fire_and_forget

    fire_and_forget(lambda: NotificationService().log_service_feedback(feedback))


# ── aggregates ──────────────────────────────────────────────────────────────

class _Window:
    """The last 30 days of one app's turn-level records, merged per turn."""

    def __init__(self, app: str, now: datetime, repository: TelemetryRepository):
        since = now - timedelta(days=WINDOW_DAYS)
        self.since = since
        # A session may have started shortly before the window.
        languages = {
            (install, session): (my or DEFAULT_MY_LANG, remote)
            for install, session, my, remote in repository.records(
                app, since - timedelta(days=1), (T.SESSION_START,), ('install_id', 'session', 'my_lang', 'target_lang'),
            )
        }
        self.turns: dict[tuple, dict] = {}
        e2e_late: dict[tuple, int] = {}
        rows = repository.records(
            app, since, (T.TURN, T.E2E),
            ('type', 'install_id', 'session', 'direction', 'turn_id', 'e2e_ms', 'model', 'app_version', 't'),
        )
        for kind, install, session, direction, turn_id, e2e, model, version, t in rows:
            key = (install, session, direction, turn_id)
            if kind == T.E2E:
                e2e_late[key] = e2e
                continue
            pair = languages.get((install, session))  # (the owner's language, the remote participant's)
            if pair and pair[1]:
                # out = the owner's speech translated into the remote's language; in = the other way round
                pair = pair if direction == 'out' else (pair[1], pair[0])
            else:
                pair = None
            self.turns[key] = {
                'install': install, 'e2e': e2e, 'model': model, 'version': version, 't': t, 'pair': pair,
            }
        for key, e2e in e2e_late.items():
            if key in self.turns and self.turns[key]['e2e'] is None:
                self.turns[key]['e2e'] = e2e

        self.errors = list(repository.records(app, since, (T.ERROR,), ('code', 'fatal')))
        latest: dict[tuple, tuple] = {}
        for install, session, direction, turn_id, rating, t in repository.records(
            app, since, (T.RATING,), ('install_id', 'session', 'direction', 'turn_id', 'rating', 't'),
        ):
            key = (install, session, direction, turn_id)
            if key not in latest or t >= latest[key][1]:  # the latest rating of a turn wins
                latest[key] = (rating, t)
        self.ratings = Counter(rating for rating, _ in latest.values())

    def e2e_values(self, turns=None) -> list[int]:
        turns = self.turns.values() if turns is None else turns
        return [turn['e2e'] for turn in turns if turn['e2e'] is not None]

    def grouped(self, attr: str) -> dict:
        groups = defaultdict(list)
        for turn in self.turns.values():
            if turn[attr]:
                groups[turn[attr]].append(turn)
        return groups

    def errors_per_100(self) -> float | None:
        if not self.turns:
            return None
        return round(len(self.errors) * 100 / len(self.turns), 1)

    def good_share(self) -> int | None:
        rated = self.ratings['good'] + self.ratings['bad']
        return round(self.ratings['good'] * 100 / rated) if rated else None


class StatsService:
    def __init__(self, repository: TelemetryRepository | None = None):
        self.repository = repository or TelemetryRepository()

    def _installs(self, app: str, now: datetime) -> dict:
        installs = AppInstall.objects.filter(app=app)
        totals = installs.aggregate(total=Count('id'), turns=Sum('turns_count'), last=Max('last_seen'))
        return {
            'installs_total': totals['total'],
            'active_7': installs.filter(last_seen__gte=now - timedelta(days=7)).count(),
            'active_30': installs.filter(last_seen__gte=now - timedelta(days=30)).count(),
            'turns_total': totals['turns'] or 0,
            'last_updated': totals['last'],
        }

    def public_stats(self, app: str, now: datetime | None = None, use_cache: bool = True) -> dict:
        key = f'apptelemetry:public:{app}'
        if use_cache and (cached := cache.get(key)) is not None:
            return cached
        stats = self._public_stats(app, now or timezone.now())
        if use_cache:
            cache.set(key, stats, PUBLIC_CACHE_SECONDS)
        return stats

    def _public_stats(self, app: str, now: datetime) -> dict:
        stats = self._installs(app, now)
        stats['empty'] = stats['installs_total'] == 0
        window = _Window(app, now, self.repository)
        stats['latency'] = _latency(window.e2e_values())
        stats['errors_per_100'] = window.errors_per_100()
        stats['good_share'] = window.good_share()

        pairs, hidden = [], False
        for pair, turns in sorted(window.grouped('pair').items()):
            if len({turn['install'] for turn in turns}) < MIN_INSTALLS:
                hidden = True
                continue
            pairs.append({'source': pair[0], 'target': pair[1], **_latency(window.e2e_values(turns))})
        stats['pairs'] = pairs

        versions = []
        active = AppInstall.objects.filter(app=app, last_seen__gte=now - timedelta(days=WINDOW_DAYS))
        rows = active.exclude(app_version='').values('app_version').annotate(n=Count('id')).order_by('-n')
        for row in rows:
            if row['n'] < MIN_INSTALLS:
                hidden = True
                continue
            versions.append({'version': row['app_version'], 'installs': row['n'],
                             'share': round(row['n'] * 100 / stats['active_30'])})
        stats['versions'] = versions
        stats['breakdowns_hidden'] = hidden
        return stats

    def owner_stats(self, app: str, now: datetime | None = None) -> dict:
        """Everything for the staff dashboard — no install threshold, never cached."""
        now = now or timezone.now()
        stats = self._installs(app, now)
        window = _Window(app, now, self.repository)
        stats['latency'] = _latency(window.e2e_values())
        stats['errors_per_100'] = window.errors_per_100()
        stats['good_share'] = window.good_share()

        by_day = defaultdict(list)
        for turn in window.turns.values():
            if turn['e2e'] is not None:
                by_day[timezone.localtime(turn['t']).date()].append(turn['e2e'])
        today = timezone.localtime(now).date()
        days = [today - timedelta(days=offset) for offset in range(WINDOW_DAYS - 1, -1, -1)]
        stats['by_day'] = [{'day': day.isoformat(), **_latency(by_day.get(day, []))} for day in days]

        def table(attr):
            rows = [{'label': label, 'installs': len({turn['install'] for turn in turns}),
                     **_latency(window.e2e_values(turns))} for label, turns in window.grouped(attr).items()]
            return sorted(rows, key=lambda row: -row['turns'])

        stats['by_model'] = table('model')
        stats['by_version'] = table('version')
        codes = Counter(code for code, _ in window.errors)
        fatal = Counter(code for code, is_fatal in window.errors if is_fatal)
        stats['errors'] = [{'code': code, 'count': n, 'fatal': fatal[code]} for code, n in codes.most_common()]
        stats['ratings'] = {key: window.ratings[key] for key in ('good', 'bad', 'none')}
        stats['feedback'] = list(AppFeedback.objects.filter(app=app).select_related('install')[:20])
        stats['feedback_total'] = AppFeedback.objects.filter(app=app).count()
        return stats
