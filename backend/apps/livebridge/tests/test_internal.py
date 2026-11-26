"""The gateway's internal calls: only on the local socket, signed, and usage charged once."""
import hashlib
import hmac
import json
import time

from core.models import SiteSettings
from django.test import TestCase, override_settings

from livebridge import devices, internal, wallet
from livebridge.models import Account, Device, LedgerEntry

SECRET = 'test-gateway-secret-0123456789abcdef'
AUTHORIZE = '/internal/livebridge/v1/authorize/'
USAGE = '/internal/livebridge/v1/usage/'


@override_settings(LIVEBRIDGE_GATEWAY_SECRET=SECRET)
class InternalCallsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def setUp(self):
        self.account = Account.objects.create(google_sub='sub-1', email='person@example.com')

    def send(self, path, body, *, timestamp=None, secret=SECRET, signature=None, **extra):
        raw = json.dumps(body).encode()
        timestamp = int(time.time()) if timestamp is None else timestamp
        signature = signature if signature is not None else internal.sign(raw, timestamp, secret)
        return self.client.post(path, data=raw, content_type='application/json',
                                HTTP_X_LIVEBRIDGE_TIMESTAMP=str(timestamp), HTTP_X_LIVEBRIDGE_SIGNATURE=signature,
                                HTTP_X_FORWARDED_PROTO='https', **extra)

    def report(self, account=None, session='sess-1', seq=1, out=10_000, inn=10_000, chars=100):
        return {'account_id': str((account or self.account).public_id), 'session_id': session, 'seq': seq,
                'stt_ms_out': out, 'stt_ms_in': inn, 'tts_chars': chars}

    def test_requests_through_the_web_server_do_not_exist(self):
        for header in ('HTTP_X_REAL_IP', 'HTTP_X_FORWARDED_FOR'):
            for path, body in ((AUTHORIZE, {'access_token': 'x'}), (USAGE, self.report())):
                response = self.send(path, body, **{header: '203.0.113.5'})
                self.assertEqual(response.status_code, 404, (header, path))
        self.assertFalse(LedgerEntry.objects.exists())

    def test_signature_and_clock(self):
        now = int(time.time())
        cases = {
            'no signature': {'signature': ''},
            'wrong signature': {'signature': internal.sign(b'{}', now, SECRET)},
            'other secret': {'secret': 'not-the-gateway-secret'},
            '61 s old': {'timestamp': now - 61},
            '61 s ahead': {'timestamp': now + 61},
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assertEqual(self.send(AUTHORIZE, {'access_token': 'x'}, **kwargs).status_code, 404)
        self.assertEqual(self.send(AUTHORIZE, {'access_token': 'x'}, timestamp=now - 59).status_code, 401)
        no_timestamp = self.client.post(AUTHORIZE, data=b'{}', content_type='application/json',
                                        HTTP_X_LIVEBRIDGE_SIGNATURE=internal.sign(b'{}', now, SECRET))
        self.assertEqual(no_timestamp.status_code, 404)
        with override_settings(LIVEBRIDGE_GATEWAY_SECRET=''):
            self.assertEqual(self.send(AUTHORIZE, {'access_token': 'x'}, secret='').status_code, 404)
        self.assertEqual(self.client.get(AUTHORIZE).status_code, 404)

    def test_sign(self):
        expected = hmac.new(b'k', b'1800000000.{"a":1}', hashlib.sha256).hexdigest()
        self.assertEqual(internal.sign(b'{"a":1}', 1_800_000_000, 'k'), expected)

    def test_authorize(self):
        grant, code = devices.start_grant('device-0001', 'Mac')
        devices.approve(grant, self.account)
        pair = devices.poll(code)
        response = self.send(AUTHORIZE, {'access_token': pair.access_token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'account_id': str(self.account.public_id), 'balance_units': 30_000,
                                           'has_purchase': False})
        devices.revoke(Device.objects.get())
        revoked = self.send(AUTHORIZE, {'access_token': pair.access_token})
        self.assertEqual((revoked.status_code, revoked.json()), (401, {'error': 'invalid_token'}))
        self.assertEqual(self.send(AUTHORIZE, {}).status_code, 401)

    def test_usage_charges_once_and_stops_at_zero(self):
        wallet.grant_trial(self.account, 'device-0001')
        first = self.send(USAGE, self.report())
        self.assertEqual((first.status_code, first.json()), (200, {'charged_units': 740, 'balance_units': 29_260}))
        again = self.send(USAGE, self.report())
        self.assertEqual(again.json(), {'charged_units': 0, 'balance_units': 29_260})

        poor = Account.objects.create(google_sub='sub-2', email='poor@example.com')
        wallet.adjust(poor, 100, 'test', 'staff@example.com')
        maximal = self.send(USAGE, self.report(poor, out=120_000, inn=120_000, chars=20_000))
        self.assertEqual(maximal.json(), {'charged_units': 100, 'balance_units': 0})
        after = self.send(USAGE, self.report(poor, seq=2))
        self.assertEqual(after.json(), {'charged_units': 0, 'balance_units': 0})
        poor.refresh_from_db()
        self.assertEqual(poor.balance_units, 0)

    def test_usage_validation(self):
        bad = [
            {'session_id': ''}, {'session_id': 'x' * 65}, {'session_id': 'has space'}, {'session_id': 7},
            {'seq': -1}, {'seq': 10**9 + 1}, {'seq': '1'}, {'seq': True},
            {'stt_ms_out': 120_001}, {'stt_ms_in': -1}, {'tts_chars': 20_001}, {'tts_chars': 1.5},
            {'account_id': 'not-a-uuid'},
        ]
        for change in bad:
            with self.subTest(change):
                response = self.send(USAGE, {**self.report(), **change})
                self.assertEqual((response.status_code, response.json()), (400, {'error': 'bad_request'}))
        for field in ('account_id', 'session_id', 'seq', 'stt_ms_out', 'stt_ms_in', 'tts_chars'):
            body = self.report()
            del body[field]
            self.assertEqual(self.send(USAGE, body).status_code, 400, field)
        unknown = self.send(USAGE, {**self.report(), 'account_id': '00000000-0000-4000-8000-00000000dead'})
        self.assertEqual((unknown.status_code, unknown.json()), (404, {'error': 'unknown_account'}))
        self.assertEqual(self.send(USAGE, {**self.report(), 'seq': 10**9}).status_code, 200)
        self.assertFalse(LedgerEntry.objects.filter(kind=LedgerEntry.USAGE, units__lt=0).exists())
