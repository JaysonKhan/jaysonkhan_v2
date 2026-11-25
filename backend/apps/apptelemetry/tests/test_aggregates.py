"""Aggregates: percentiles, the 5-install rule for breakdowns, the empty state."""
import uuid
from datetime import timedelta
from unittest import TestCase as PlainTestCase

from apptelemetry.models import AppInstall, TelemetryRecord
from apptelemetry.services import StatsService, percentile
from django.utils import timezone

from .helpers import ServicesTestCase, recent, session_start, turn


class PercentileTest(PlainTestCase):
    def test_known_values(self):
        values = list(range(1, 101))  # 1..100
        self.assertEqual(percentile(values, 50), 50.5)
        self.assertAlmostEqual(percentile(values, 95), 95.05)
        self.assertEqual(percentile([4, 1, 3, 2], 50), 2.5)  # order does not matter
        self.assertEqual(percentile([700], 95), 700)
        self.assertIsNone(percentile([], 50))


class StatsTest(ServicesTestCase):
    def stats(self):
        return StatsService().public_stats('livebridge', use_cache=False)

    def add_install(self, e2e_values, target='en', version='1.0.0+1', direction='out'):
        records = [session_start(target=target)] + [
            turn(turn_id=i, e2e=value, direction=direction, minutes=9 - i % 5) for i, value in enumerate(e2e_values)
        ]
        response = self.send(records, str(uuid.uuid4()), app_version=version)
        self.assertEqual(response.status_code, 202, response.content)

    def test_empty_state(self):
        stats = self.stats()
        self.assertTrue(stats['empty'])
        self.assertEqual((stats['installs_total'], stats['turns_total']), (0, 0))
        self.assertIsNone(stats['latency']['p50'])
        self.assertIsNone(stats['errors_per_100'])
        self.assertIsNone(stats['good_share'])
        self.assertEqual((stats['pairs'], stats['versions']), ([], []))

    def test_overall_percentiles_on_a_known_data_set(self):
        # Five installs x 20 turns: e2e 100, 200, ... 10 000 ms
        values = [100 * i for i in range(1, 101)]
        for n in range(5):
            self.add_install(values[n * 20:(n + 1) * 20])
        stats = self.stats()
        self.assertEqual(stats['latency'], {'turns': 100, 'p50': 5050, 'p95': 9505})
        self.assertEqual((stats['installs_total'], stats['active_7'], stats['active_30'], stats['turns_total']),
                         (5, 5, 5, 100))
        self.assertFalse(stats['empty'])

    def test_breakdowns_are_hidden_below_five_installs(self):
        for _ in range(4):
            self.add_install([1000, 2000], target='en')
        stats = self.stats()
        self.assertEqual(stats['pairs'], [])
        self.assertEqual(stats['versions'], [])
        self.assertTrue(stats['breakdowns_hidden'])
        self.assertEqual(stats['latency']['p50'], 1500)  # the overall figure is still shown

        self.add_install([1000, 2000], target='en')
        stats = self.stats()
        self.assertEqual(stats['pairs'], [{'source': 'uz', 'target': 'en', 'turns': 10, 'p50': 1500, 'p95': 2000}])
        self.assertEqual(stats['versions'], [{'version': '1.0.0+1', 'installs': 5, 'share': 100}])
        self.assertFalse(stats['breakdowns_hidden'])

    def test_each_breakdown_row_needs_five_installs(self):
        for _ in range(5):
            self.add_install([800], target='ru', version='1.1.0+2')
        for _ in range(2):
            self.add_install([900], target='en', version='1.0.0+1', direction='in')
        stats = self.stats()
        self.assertEqual([(p['source'], p['target']) for p in stats['pairs']], [('uz', 'ru')])
        self.assertEqual(stats['versions'], [{'version': '1.1.0+2', 'installs': 5, 'share': 71}])
        self.assertTrue(stats['breakdowns_hidden'])

    def test_errors_ratings_and_late_e2e(self):
        install_id = str(uuid.uuid4())
        records = [
            session_start(),
            turn(turn_id=1, e2e=1000),
            turn(turn_id=2, e2eMs=None),
            {'type': 'e2e', 't': recent(5), 'session': 1, 'direction': 'out', 'turnId': 2, 'e2eMs': 3000},
            turn(turn_id=3, e2e=2000), turn(turn_id=4, e2e=2000),
            {'type': 'error', 't': recent(5), 'session': 1, 'code': 'stt_closed', 'fatal': True},
            {'type': 'rating', 't': recent(6), 'session': 1, 'direction': 'out', 'turnId': 1, 'rating': 'bad'},
            {'type': 'rating', 't': recent(4), 'session': 1, 'direction': 'out', 'turnId': 1, 'rating': 'good'},
            {'type': 'rating', 't': recent(4), 'session': 1, 'direction': 'out', 'turnId': 2, 'rating': 'bad'},
            {'type': 'rating', 't': recent(4), 'session': 1, 'direction': 'out', 'turnId': 3, 'rating': 'none'},
        ]
        self.send(records, install_id)
        stats = self.stats()
        self.assertEqual(stats['latency'], {'turns': 4, 'p50': 2000, 'p95': 2850})
        self.assertEqual(stats['errors_per_100'], 25.0)
        self.assertEqual(stats['good_share'], 50)  # turn 1: latest = good; turn 2: bad; 'none' is not a judgement

        owner = StatsService().owner_stats('livebridge')
        self.assertEqual(owner['ratings'], {'good': 1, 'bad': 1, 'none': 1})
        self.assertEqual(owner['errors'], [{'code': 'stt_closed', 'count': 1, 'fatal': 1}])
        self.assertEqual(owner['by_model'][0]['label'], 'gemini-3.5-flash-lite')
        self.assertEqual(len(owner['by_day']), 30)
        self.assertEqual(sum(day['turns'] for day in owner['by_day']), 4)

    def test_window_is_the_last_30_days(self):
        self.add_install([1000])
        TelemetryRecord.objects.filter(type='turn').update(t=timezone.now() - timedelta(days=31))
        stats = self.stats()
        self.assertEqual(stats['latency']['turns'], 0)
        self.assertEqual(stats['turns_total'], 1)  # the lifetime counter is kept
        AppInstall.objects.update(last_seen=timezone.now() - timedelta(days=10))
        stats = self.stats()
        self.assertEqual((stats['active_7'], stats['active_30']), (0, 1))
