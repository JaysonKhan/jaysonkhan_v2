"""Connecting the app with a short code (device grant) and the device's rotating tokens."""
import re
from datetime import datetime, timedelta, timezone

from django.test import TestCase

from livebridge import devices
from livebridge.models import Account, Device, DeviceGrant

T0 = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
CODE_RE = re.compile(r'^[B-DF-HJ-NP-TV-XZ]{4}-[B-DF-HJ-NP-TV-XZ]{4}$')


def make_account(n=1):
    return Account.objects.create(google_sub=f'sub-{n}', email=f'a{n}@example.com')


def at(seconds):
    return T0 + timedelta(seconds=seconds)


class DevicesTest(TestCase):
    def setUp(self):
        self.account = make_account()

    def connect(self, account=None, device_id='device-0001', now=T0):
        grant, code = devices.start_grant(device_id, 'Work Mac', now=now)
        devices.approve(grant, account or self.account, now=now)
        pair = devices.poll(code, now=now + timedelta(seconds=6))
        self.assertIsInstance(pair, devices.TokenPair)
        return pair

    def test_user_code_shape_and_normalising(self):
        grant, _ = devices.start_grant('device-0001', 'Mac', now=T0)
        self.assertRegex(grant.user_code, CODE_RE)
        self.assertEqual(devices.normalize_user_code('bcdf ghjk'), 'BCDF-GHJK')
        self.assertEqual(devices.normalize_user_code(' bcdf-ghjk '), 'BCDF-GHJK')
        self.assertIsNone(devices.normalize_user_code('ABCD-1234'))
        self.assertIsNone(devices.normalize_user_code('BCDF-GHJ'))
        self.assertIsNone(devices.normalize_user_code(''))
        self.assertEqual(devices.find_pending_grant(grant.user_code.lower(), now=T0), grant)

    def test_bad_device_id_is_refused(self):
        for bad in ('short', 'has space inside', 'x' * 65, 'semi;colon-id', ''):
            with self.assertRaises(ValueError):
                devices.start_grant(bad, 'Mac', now=T0)
        grant, _ = devices.start_grant('device-0001', '\x00\x07  ', now=T0)
        self.assertEqual(grant.device_name, 'LiveBridge')
        grant, _ = devices.start_grant('device-0001', 'M' * 200, now=T0)
        self.assertEqual(len(grant.device_name), 80)

    def test_poll_sequence(self):
        grant, code = devices.start_grant('device-0001', 'Mac', now=T0)
        self.assertEqual(devices.poll(code, now=at(1)), 'authorization_pending')
        self.assertEqual(devices.poll(code, now=at(3)), 'slow_down')
        grant.refresh_from_db()
        self.assertEqual(grant.interval, 10)
        self.assertEqual(devices.approve(grant, self.account, now=at(4)), 'granted')
        pair = devices.poll(code, now=at(20))
        self.assertIsInstance(pair, devices.TokenPair)
        self.assertEqual(pair.expires_in, 15 * 60)
        self.assertEqual(devices.poll(code, now=at(40)), 'invalid_grant')
        self.assertEqual(devices.poll('lbd_unknown', now=at(40)), 'invalid_grant')

    def test_denied_and_expired_grants_never_give_tokens(self):
        grant, code = devices.start_grant('device-0001', 'Mac', now=T0)
        devices.deny(grant)
        self.assertEqual(devices.poll(code, now=at(10)), 'access_denied')
        self.assertEqual(devices.poll(code, now=at(20)), 'access_denied')
        self.assertIsNone(devices.find_pending_grant(grant.user_code, now=at(10)))

        late, late_code = devices.start_grant('device-0002', 'Mac', now=T0)
        self.assertEqual(devices.poll(late_code, now=late.expires_at + timedelta(seconds=1)), 'expired_token')
        self.assertIsNone(devices.find_pending_grant(late.user_code, now=late.expires_at + timedelta(seconds=1)))

        approved, approved_code = devices.start_grant('device-0003', 'Mac', now=T0)
        devices.approve(approved, self.account, now=at(5))
        self.assertEqual(devices.poll(approved_code, now=approved.expires_at + timedelta(seconds=1)), 'expired_token')
        self.assertFalse(Device.objects.exists())

    def test_approve_stores_trial_outcome(self):
        grant, _ = devices.start_grant('device-0001', 'Mac', now=T0)
        self.assertEqual(devices.approve(grant, self.account, now=T0), 'granted')
        grant.refresh_from_db()
        self.assertEqual((grant.status, grant.account, grant.trial_outcome), (DeviceGrant.APPROVED, self.account,
                                                                              'granted'))
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_units, 30_000)

    def test_reconnecting_the_same_device_signs_out_the_old_one(self):
        first = self.connect()
        second = self.connect(now=at(60))
        self.assertIsNone(devices.authenticate(first.access_token, now=at(70)))
        self.assertIsNotNone(devices.authenticate(second.access_token, now=at(70)))
        self.assertEqual(Device.objects.filter(revoked_at__isnull=True).count(), 1)
        other = self.connect(device_id='device-0002', now=at(80))
        self.assertIsNotNone(devices.authenticate(other.access_token, now=at(90)))
        self.assertIsNotNone(devices.authenticate(second.access_token, now=at(90)))

    def test_refresh_rotates(self):
        old = self.connect()
        new = devices.refresh(old.refresh_token, now=at(600))
        self.assertIsInstance(new, devices.TokenPair)
        self.assertNotEqual(new.access_token, old.access_token)
        self.assertNotEqual(new.refresh_token, old.refresh_token)
        self.assertIsNotNone(devices.authenticate(new.access_token, now=at(610)))
        self.assertIsNone(devices.authenticate(old.access_token, now=at(610)))
        self.assertIsInstance(devices.refresh(new.refresh_token, now=at(700)), devices.TokenPair)

    def test_refresh_reuse_revokes_the_device(self):
        a = self.connect()
        b = devices.refresh(a.refresh_token, now=at(600))
        self.assertIsNone(devices.refresh(a.refresh_token, now=at(601)))
        self.assertIsNotNone(Device.objects.get().revoked_at)
        self.assertIsNone(devices.authenticate(b.access_token, now=at(602)))
        self.assertIsNone(devices.refresh(b.refresh_token, now=at(603)))

    def test_refresh_refuses_expired_and_unknown(self):
        pair = self.connect()
        self.assertIsNone(devices.refresh('lbr_unknown', now=at(10)))
        self.assertIsNone(devices.refresh(pair.refresh_token, now=T0 + devices.REFRESH_TTL + timedelta(days=1)))

    def test_authenticate_rejects_expired_revoked_inactive_and_deletion_requested(self):
        pair = self.connect()
        device = devices.authenticate(pair.access_token, now=at(60))
        self.assertIsNotNone(device)
        self.assertIsNotNone(device.last_used_at)
        self.account.refresh_from_db()
        self.assertIsNotNone(self.account.last_seen_at)
        self.assertIsNone(devices.authenticate(pair.access_token, now=T0 + devices.ACCESS_TTL + timedelta(minutes=1)))
        self.assertIsNone(devices.authenticate('lba_unknown', now=at(60)))

        Account.objects.filter(pk=self.account.pk).update(deletion_requested_at=at(61))
        self.assertIsNone(devices.authenticate(pair.access_token, now=at(62)))
        Account.objects.filter(pk=self.account.pk).update(deletion_requested_at=None, is_active=False)
        self.assertIsNone(devices.authenticate(pair.access_token, now=at(63)))
        Account.objects.filter(pk=self.account.pk).update(is_active=True)
        self.assertIsNotNone(devices.authenticate(pair.access_token, now=at(64)))

        devices.revoke(Device.objects.get(), now=at(65))
        self.assertIsNone(devices.authenticate(pair.access_token, now=at(66)))
        self.assertIsNone(devices.refresh(pair.refresh_token, now=at(67)))

    def test_only_hashes_are_stored(self):
        grant, code = devices.start_grant('device-0001', 'Mac', now=T0)
        devices.approve(grant, self.account, now=T0)
        pair = devices.poll(code, now=at(6))
        rotated = devices.refresh(pair.refresh_token, now=at(60))
        plain = [code, pair.access_token, pair.refresh_token, rotated.access_token, rotated.refresh_token]
        for model in (Device, DeviceGrant):
            for row in model.objects.all():
                stored = ' '.join(str(getattr(row, f.attname)) for f in model._meta.concrete_fields)
                for value in plain:
                    self.assertNotIn(value, stored)
                    self.assertNotIn(value[4:], stored)
        self.assertTrue(code.startswith('lbd_') and pair.access_token.startswith('lba_')
                        and pair.refresh_token.startswith('lbr_'))
