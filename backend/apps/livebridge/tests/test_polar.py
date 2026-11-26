"""The Polar webhook: Standard Webhooks signatures, purchases credited once, refunds in proportion."""
import base64
import copy
import hashlib
import hmac
import json
import time
import uuid
from pathlib import Path

from unittest import mock

from django.test import TestCase, override_settings

from livebridge import polar, wallet
from livebridge.models import Account, LedgerEntry, Package

URL = '/api/livebridge/v1/polar/webhook/'
SECRET = 'whsec_' + base64.b64encode(b'test-webhook-key-0123456789abcdef').decode()
ACCOUNT_ID = uuid.UUID('00000000-0000-4000-8000-000000000001')
PRODUCT_ID = '00000000-0000-4000-8000-000000000002'
ORDER_ID = '00000000-0000-4000-8000-000000000003'
FIXTURES = Path(__file__).parent / 'fixtures'


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def signature(body: bytes, timestamp: int, msg_id: str, key: bytes) -> str:
    digest = hmac.new(key, f'{msg_id}.{timestamp}.'.encode() + body, hashlib.sha256).digest()
    return 'v1,' + base64.b64encode(digest).decode()


STANDARD_KEY = base64.b64decode(SECRET[len('whsec_'):])


@override_settings(POLAR_WEBHOOK_SECRET=SECRET)
class PolarWebhookTest(TestCase):
    def setUp(self):
        self.account = Account.objects.create(google_sub='sub-1', email='person@example.com', public_id=ACCOUNT_ID)
        Package.objects.filter(code='starter').update(polar_product_id=PRODUCT_ID)
        self.starter_units = Package.objects.get(code='starter').units

    def deliver(self, event, *, timestamp=None, msg_id='msg_test_1', key=STANDARD_KEY, sig=None, body=None):
        body = body if body is not None else json.dumps(event).encode()
        timestamp = int(time.time()) if timestamp is None else timestamp
        sig = sig if sig is not None else signature(body, timestamp, msg_id, key)
        return self.client.post(URL, data=body, content_type='application/json', HTTP_WEBHOOK_ID=msg_id,
                                HTTP_WEBHOOK_TIMESTAMP=str(timestamp), HTTP_WEBHOOK_SIGNATURE=sig)

    def balance(self):
        self.account.refresh_from_db()
        return self.account.balance_units

    def test_signature_valid_wrong_and_stale(self):
        event = {'type': 'checkout.updated', 'data': {}}
        self.assertEqual(self.deliver(event).status_code, 202)
        body = json.dumps(event).encode()
        now = int(time.time())
        good = signature(body, now, 'msg_test_1', STANDARD_KEY)
        tampered = body.replace(b'checkout', b'checkouT')
        self.assertEqual(self.deliver(event, body=tampered, sig=good, timestamp=now).status_code, 403)
        self.assertEqual(self.deliver(event, timestamp=now - 301).status_code, 403)
        self.assertEqual(self.deliver(event, timestamp=now + 301).status_code, 403)
        two = 'v1,' + base64.b64encode(b'x' * 32).decode() + ' ' + good
        self.assertEqual(self.deliver(event, sig=two, timestamp=now).status_code, 202)
        self.assertEqual(self.deliver(event, sig='v2,' + good[3:], timestamp=now).status_code, 403)
        self.assertEqual(self.client.post(URL, data=body, content_type='application/json').status_code, 403)
        with override_settings(POLAR_WEBHOOK_SECRET=''):
            self.assertEqual(self.deliver(event).status_code, 403)

    def test_endpoints_made_before_standard_webhooks_are_accepted(self):
        # Polar's original scheme: the key is the UTF-8 bytes of the whole secret string.
        self.assertEqual(self.deliver({'type': 'x', 'data': {}}, key=SECRET.encode()).status_code, 202)

    def test_verify_webhook_directly(self):
        body, now = b'{}', 1_800_000_000
        headers = {'webhook-id': 'm1', 'webhook-timestamp': str(now),
                   'webhook-signature': signature(body, now, 'm1', STANDARD_KEY)}
        self.assertTrue(polar.verify_webhook(body, headers, SECRET, now=now + 300))
        self.assertFalse(polar.verify_webhook(body, headers, SECRET, now=now + 301))
        self.assertFalse(polar.verify_webhook(body, {**headers, 'webhook-timestamp': 'soon'}, SECRET, now=now))
        self.assertFalse(polar.verify_webhook(body, headers, '', now=now))

    def test_bad_json_is_refused(self):
        self.assertEqual(self.deliver(None, body=b'{not json').status_code, 400)

    def test_order_paid_credits_once(self):
        event = fixture('order_paid.json')
        self.assertEqual(self.deliver(event, msg_id='msg_1').status_code, 202)
        self.assertEqual(self.deliver(event, msg_id='msg_1').status_code, 202)  # Polar retried a slow delivery
        self.assertEqual(self.balance(), self.starter_units)
        entry = LedgerEntry.objects.get()
        self.assertEqual((entry.kind, entry.reference), (LedgerEntry.PURCHASE, ORDER_ID))
        self.assertEqual(entry.details, {'package': 'starter', 'total_cents': 500, 'net_cents': 500, 'currency': 'usd'})
        self.assertTrue(wallet.has_purchase(self.account))

    def test_order_paid_falls_back_to_the_metadata_account(self):
        event = fixture('order_paid.json')
        event['data']['customer']['external_id'] = None
        self.deliver(event)
        self.assertEqual(self.balance(), self.starter_units)

    def test_unmatched_order_is_logged_not_credited(self):
        for name, change in (('product', lambda d: d.update(product_id='unknown-product')),
                             ('account', lambda d: (d['customer'].update(external_id=str(uuid.uuid4())),
                                                    d['metadata'].update(account='not-a-uuid')))):
            with self.subTest(name):
                event = fixture('order_paid.json')
                change(event['data'])
                with self.assertLogs('livebridge', 'ERROR') as logs:
                    self.assertEqual(self.deliver(event).status_code, 202)
                self.assertIn(f'order={ORDER_ID}', logs.output[0])
                self.assertNotIn('buyer@example.com', ' '.join(logs.output))
        self.assertFalse(LedgerEntry.objects.exists())
        self.assertEqual(self.balance(), 0)

    def test_unmatched_order_alerts_the_owner(self):
        event = fixture('order_paid.json')
        event['data']['product_id'] = 'unknown-product'
        with mock.patch('livebridge.alerts.owner_alert') as alert, self.assertLogs('livebridge', 'ERROR'):
            self.deliver(event)
        alert.assert_called_once_with('unmatched_order', order=ORDER_ID)
        refund = fixture('order_refunded.json')
        refund['data']['id'] = 'unknown-order'
        with mock.patch('livebridge.alerts.owner_alert') as alert, self.assertLogs('livebridge', 'ERROR'):
            self.deliver(refund)
        alert.assert_called_once_with('unmatched_refund', order='unknown-order')

    def test_checkout_metadata_wins_over_a_stale_customer_id(self):
        other = Account.objects.create(google_sub='sub-2', email='other@example.com')
        event = fixture('order_paid.json')
        event['data']['customer']['external_id'] = str(other.public_id)  # an older id on the same Polar customer
        self.deliver(event)
        self.assertEqual(self.balance(), self.starter_units)
        other.refresh_from_db()
        self.assertEqual(other.balance_units, 0)

    def test_partial_then_full_refund(self):
        self.deliver(fixture('order_paid.json'))
        partial = fixture('order_refunded.json')
        self.deliver(partial, msg_id='msg_r1')
        half = self.starter_units * 250 // 500
        self.assertEqual(self.balance(), self.starter_units - half)
        full = copy.deepcopy(partial)
        full['data'].update(refunded_amount=500, status='refunded')
        self.deliver(full, msg_id='msg_r2')
        self.assertEqual(self.balance(), 0)
        self.deliver(full, msg_id='msg_r2')
        self.deliver(partial, msg_id='msg_r1')
        refunds = LedgerEntry.objects.filter(kind=LedgerEntry.REFUND).order_by('pk')
        self.assertEqual([r.units for r in refunds], [-half, -(self.starter_units - half)])
        self.assertEqual(refunds[0].details, {'order': ORDER_ID, 'refunded_cents': 250, 'asked': half})
        self.assertEqual(self.balance(), 0)

    def test_refund_never_goes_below_zero(self):
        self.deliver(fixture('order_paid.json'))
        wallet.record_usage(self.account, 'sess', 1, 0, 0, (self.starter_units - 50_000) // 5)  # all but 50 000 used
        self.assertEqual(self.balance(), 50_000)
        full = fixture('order_refunded.json')
        full['data']['refunded_amount'] = 500
        self.deliver(full)
        self.assertEqual(self.balance(), 0)
        self.assertEqual(LedgerEntry.objects.get(kind=LedgerEntry.REFUND).units, -50_000)

    def test_refund_for_an_unknown_order_is_logged(self):
        with self.assertLogs('livebridge', 'ERROR'):
            self.assertEqual(self.deliver(fixture('order_refunded.json')).status_code, 202)
        self.assertFalse(LedgerEntry.objects.exists())

    def test_unknown_event_is_accepted(self):
        response = self.deliver({'type': 'subscription.created', 'data': {'id': 'x'}})
        self.assertEqual(response.status_code, 202)
        self.assertFalse(LedgerEntry.objects.exists())
