"""Fetch weekly WakaTime stats into SiteSettings.wakatime_stats.

Feeds the homepage WakaTime widget (XIVA INK design). Reads the API key from
the WAKATIME_API_KEY env var; if unset or the API fails, existing stats are
left untouched (widget keeps showing last good data).

Cron: weekly/daily via ops cron_run or crontab:
    venv/bin/python manage.py fetch_wakatime
"""
import base64
import datetime
import logging
import os

import httpx
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

API_BASE = 'https://wakatime.com/api/v1/users/current'
# Day labels — uz two-letter weekday abbreviations, Monday-first (design uses Du/Se/Ch/Pa/Ju/Sh/Ya)
DAY_LABELS = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']


class Command(BaseCommand):
    help = 'Fetch last-7-days WakaTime stats into SiteSettings.wakatime_stats'

    def handle(self, *args, **options):
        api_key = os.environ.get('WAKATIME_API_KEY', '').strip()
        if not api_key:
            self.stdout.write(self.style.WARNING('WAKATIME_API_KEY not set — skipping.'))
            return

        headers = {
            'Authorization': 'Basic ' + base64.b64encode(api_key.encode()).decode()
        }

        try:
            with httpx.Client(timeout=20, headers=headers) as client:
                summaries = client.get(f'{API_BASE}/summaries', params={'range': 'last_7_days'})
                summaries.raise_for_status()
                stats = client.get(f'{API_BASE}/stats/last_7_days')
                stats.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning('WakaTime fetch failed: %s', exc)
            self.stderr.write(self.style.ERROR(f'WakaTime API error: {exc}'))
            return

        days_raw = summaries.json().get('data', [])
        stats_data = stats.json().get('data', {})

        days = []
        for entry in days_raw[-7:]:
            seconds = (entry.get('grand_total') or {}).get('total_seconds', 0)
            iso = (entry.get('range') or {}).get('date', '')
            try:
                weekday = datetime.date.fromisoformat(iso).weekday()
                label = DAY_LABELS[weekday]
            except ValueError:
                label = '—'
            days.append({'d': label, 'h': round(seconds / 3600, 1)})

        max_h = max((d['h'] for d in days), default=0) or 1
        for d in days:
            d['pct'] = max(4, round(d['h'] / max_h * 100))
            d['peak'] = d['h'] == max_h and max_h > 0

        langs = [
            {'name': l['name'], 'pct': round(l['percent'])}
            for l in stats_data.get('languages', [])[:5]
        ]
        total = round(sum(d['h'] for d in days), 1)

        from core.models import SiteSettings
        settings_obj = SiteSettings.load()
        settings_obj.wakatime_stats = {'total': total, 'days': days, 'langs': langs}
        settings_obj.save(update_fields=['wakatime_stats'])

        self.stdout.write(self.style.SUCCESS(
            f'WakaTime updated: {total}h across {len(days)} days, {len(langs)} languages.'
        ))
