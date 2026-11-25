"""POST /api/services/v1/telemetry/ against the v1 contract (LiveBridge docs/telemetry-api.md)."""
import json
import uuid
from unittest import mock

from apptelemetry import ratelimit
from apptelemetry.models import AppFeedback, AppInstall, TelemetryRecord
from django.core.cache import cache
from django.test import Client

from .helpers import (
    CLIENT_IP,
    TELEMETRY_URL,
    ServicesTestCase,
    envelope,
    recent,
    session_start,
    turn,
)


class TelemetryHappyPathTest(ServicesTestCase):
    def test_stores_records_and_the_install(self):
        install_id = str(uuid.uuid4())
        records = [
            session_start(),
            turn(turn_id=1),
            {'type': 'rating', 't': recent(8), 'session': 1, 'direction': 'out', 'turnId': 1, 'rating': 'good'},
            {'type': 'error', 't': recent(8), 'session': 1, 'code': 'tts_timeout', 'direction': 'in', 'fatal': False},
            {'type': 'reconnect', 't': recent(7), 'session': 1},
            {'type': 'empty_turn', 't': recent(7), 'session': 1, 'direction': 'in'},
            {'type': 'e2e', 't': recent(6), 'session': 1, 'direction': 'in', 'turnId': 2, 'e2eMs': 1500},
            {'type': 'session_end', 't': recent(5), 'session': 1, 'durationSec': 193, 'turns': 7},
        ]
        response = self.send(records, install_id)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {'accepted': 8, 'ignored': 0})

        install = AppInstall.objects.get(install_id=install_id)
        self.assertEqual((install.app, install.app_version, install.os_version, install.ui_language),
                         ('livebridge', '1.0.0+1', 'macOS 26.6.2', 'uz'))
        self.assertEqual(install.turns_count, 1)
        self.assertEqual(install.records.count(), 8)
        stored = install.records.get(type='turn')
        self.assertEqual((stored.direction, stored.turn_id, stored.e2e_ms, stored.stt_commit_ms, stored.model),
                         ('out', 1, 1350, 302, 'gemini-3.5-flash-lite'))
        self.assertEqual(install.records.get(type='session_start').target_lang, 'en')
        self.assertFalse(install.records.get(type='error').fatal)

    def test_no_cookies_and_csrf_is_not_required(self):
        response = self.post_json(TELEMETRY_URL, envelope([turn()]), client=Client(enforce_csrf_checks=True))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(response.cookies), 0)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(TELEMETRY_URL).status_code, 405)


class TelemetryEnvelopeTest(ServicesTestCase):
    def assertError(self, response, status, code):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.json(), {'error': code})

    def test_invalid_envelopes_are_400(self):
        self.assertError(self.post_json(TELEMETRY_URL, '{not json'), 400, 'bad_json')
        self.assertError(self.post_json(TELEMETRY_URL, '[1, 2]'), 400, 'bad_json')
        self.assertError(self.send([turn()], install_id='not-a-uuid'), 400, 'bad_install_id')
        self.assertError(self.send([turn()], install_id=str(uuid.uuid1())), 400, 'bad_install_id')  # not v4
        self.assertError(self.send([turn()], schema=2), 400, 'bad_schema')
        self.assertError(self.send([]), 400, 'no_records')
        self.assertError(self.send('nope'), 400, 'no_records')
        self.assertFalse(AppInstall.objects.exists())

    def test_unknown_app_is_400(self):
        self.assertError(self.send([turn()], app='otherapp'), 400, 'unknown_app')

    def test_more_than_500_records_is_413(self):
        records = [turn(turn_id=i) for i in range(501)]
        self.assertError(self.send(records), 413, 'too_large')
        self.assertEqual(self.send(records[:500]).status_code, 202)

    def test_body_over_256_kb_is_413(self):
        body = json.dumps(envelope([turn()], padding='x' * (256 * 1024)))
        self.assertError(self.post_json(TELEMETRY_URL, body), 413, 'too_large')
        self.assertFalse(TelemetryRecord.objects.exists())


class TelemetryRecordRulesTest(ServicesTestCase):
    def test_unknown_record_keys_are_ignored(self):
        record = turn(transcript='salom dunyo', deviceName='MacBook')
        response = self.send([record], extra_envelope_key='whatever')
        self.assertEqual(response.json(), {'accepted': 1, 'ignored': 0})
        row = TelemetryRecord.objects.values().get()
        self.assertNotIn('salom dunyo', json.dumps(row, default=str))

    def test_out_of_range_integers_are_clamped(self):
        self.send([turn(e2e=9_999_999, sttCommitMs=-5, sourceChars=600_001)])
        row = TelemetryRecord.objects.get()
        self.assertEqual((row.e2e_ms, row.stt_commit_ms, row.source_chars), (600_000, 0, 600_000))

    def test_bad_records_are_counted_as_ignored(self):
        records = [
            turn(turn_id=1),
            {'type': 'bogus', 't': recent(), 'session': 1},
            {'type': 'turn', 't': recent(), 'session': 1, 'turnId': 2},  # no direction
            {'type': 'turn', 't': 'yesterday', 'session': 1, 'direction': 'out', 'turnId': 3},
            {'type': 'turn', 't': recent(), 'session': -1, 'direction': 'out', 'turnId': 4},
            {'type': 'rating', 't': recent(), 'session': 1, 'direction': 'out', 'turnId': 1, 'rating': 'meh'},
            {'type': 'error', 't': recent(), 'session': 1, 'code': 'Bad Code!'},
            {'type': 'session_start', 't': recent(), 'session': 1, 'mode': 'x', 'targetLang': 'en', 'outCommit': 'vad'},
            {'type': 'turn', 't': '2999-01-01T00:00:00Z', 'session': 1, 'direction': 'out', 'turnId': 5},
            'not a record',
        ]
        self.assertEqual(self.send(records).json(), {'accepted': 1, 'ignored': 9})

    def test_session_languages_are_any_two_different_codes(self):
        records = [
            session_start(session=1, target='tr', my='en'),      # any pair
            session_start(session=2, target='yue'),              # three-letter code; no myLang = Uzbek
            session_start(session=3, target='English'),          # not a code
            session_start(session=4, target='EN'),
            session_start(session=5, target='de', my='de'),      # a language into itself
            {**session_start(session=6), 'targetLang': 7},
            {**session_start(session=7, target='en'), 'myLang': 'x'},
        ]
        self.assertEqual(self.send(records).json(), {'accepted': 2, 'ignored': 5})
        stored = TelemetryRecord.objects.filter(type='session_start').order_by('session')
        self.assertEqual([(r.session, r.my_lang, r.target_lang) for r in stored], [(1, 'en', 'tr'), (2, 'uz', 'yue')])

    def test_resending_a_batch_stores_nothing_twice(self):
        install_id = str(uuid.uuid4())
        records = [session_start(), turn(turn_id=1), turn(turn_id=2, minutes=8)]
        self.assertEqual(self.send(records, install_id).json(), {'accepted': 3, 'ignored': 0})
        self.assertEqual(self.send(records, install_id).json(), {'accepted': 0, 'ignored': 3})
        # A batch that overlaps the last one: only the new record counts; duplicates inside one batch too.
        newer = turn(turn_id=3, minutes=7)
        self.assertEqual(self.send(records + [newer, newer], install_id).json(), {'accepted': 1, 'ignored': 4})
        self.assertEqual(TelemetryRecord.objects.count(), 4)
        self.assertEqual(AppInstall.objects.get(install_id=install_id).turns_count, 3)


class TelemetryDedupKeyTest(ServicesTestCase):
    def test_direction_is_part_of_the_dedup_key(self):
        install_id = str(uuid.uuid4())
        t = recent(3)
        out_turn = {'type': 'turn', 't': t, 'session': 2, 'direction': 'out', 'turnId': 5, 'e2eMs': 1200}
        in_turn = {**out_turn, 'direction': 'in', 'e2eMs': 1400}
        self.assertEqual(self.send([out_turn, in_turn], install_id).json(), {'accepted': 2, 'ignored': 0})
        self.assertEqual(sorted(TelemetryRecord.objects.values_list('direction', 'e2e_ms')),
                         [('in', 1400), ('out', 1200)])
        self.assertEqual(self.send([out_turn, in_turn], install_id).json(), {'accepted': 0, 'ignored': 2})
        self.assertEqual(TelemetryRecord.objects.count(), 2)
        self.assertEqual(AppInstall.objects.get(install_id=install_id).turns_count, 2)

    def test_records_without_direction_or_turn_still_dedupe(self):
        install_id = str(uuid.uuid4())
        records = [session_start(), {'type': 'reconnect', 't': recent(2), 'session': 1}]
        self.send(records, install_id)
        self.assertEqual(self.send(records, install_id).json(), {'accepted': 0, 'ignored': 2})
        self.assertEqual(set(TelemetryRecord.objects.values_list('direction', 'turn_id')), {('', 0)})


class TelemetryRateLimitTest(ServicesTestCase):
    def test_contract_limits(self):
        self.assertEqual((ratelimit.TELEMETRY_PER_ADDRESS.max_count, ratelimit.TELEMETRY_PER_ADDRESS.window),
                         (60, 3600))
        self.assertEqual((ratelimit.RECORDS_PER_INSTALL.max_count, ratelimit.RECORDS_PER_INSTALL.window),
                         (20_000, 86400))
        self.assertEqual((ratelimit.FEEDBACK_PER_ADDRESS.max_count, ratelimit.FEEDBACK_PER_ADDRESS.window),
                         (5, 3600))

    def test_too_many_requests_per_address_is_429_with_retry_after(self):
        with mock.patch.object(ratelimit, 'TELEMETRY_PER_ADDRESS', ratelimit.Limit('tel_addr', 2, 3600)):
            self.assertEqual(self.send([turn()]).status_code, 202)
            self.assertEqual(self.send([turn()]).status_code, 202)
            response = self.send([turn()])
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.json(), {'error': 'rate_limited'})
            self.assertTrue(0 < int(response['Retry-After']) <= 3600)
            # Another address has its own budget.
            self.assertEqual(self.send([turn()], ip='198.51.100.9').status_code, 202)

    def test_too_many_records_per_install_is_429(self):
        install_id = str(uuid.uuid4())
        with mock.patch.object(ratelimit, 'RECORDS_PER_INSTALL', ratelimit.Limit('tel_inst', 3, 86400)):
            self.assertEqual(self.send([turn(turn_id=1), turn(turn_id=2)], install_id).status_code, 202)
            response = self.send([turn(turn_id=3), turn(turn_id=4)], install_id)
            self.assertEqual(response.status_code, 429)
            self.assertIn('Retry-After', response)

    def test_no_raw_ip_is_stored_anywhere(self):
        self.send([session_start(), turn()])
        self.post_json('/api/services/v1/feedback/', {'app': 'livebridge', 'message': 'Zo\'r!'})
        for model in (AppInstall, TelemetryRecord, AppFeedback):
            for row in model.objects.values():
                self.assertNotIn(CLIENT_IP, json.dumps(row, default=str), model.__name__)
        keys = list(getattr(cache, '_cache', {}).keys())
        self.assertTrue(keys)
        self.assertFalse([key for key in keys if CLIENT_IP in str(key)])
