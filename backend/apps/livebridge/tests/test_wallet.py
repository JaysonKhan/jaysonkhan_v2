"""The wallet: every balance change, applied once per reference, never below zero."""
from datetime import datetime, timezone

from django.test import TestCase, override_settings

from livebridge import wallet
from livebridge.models import Account, LedgerEntry, TrialDevice

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


def make_account(n=1):
    return Account.objects.create(google_sub=f'sub-{n}', email=f'a{n}@example.com')


class WalletTest(TestCase):
    def setUp(self):
        self.account = make_account()

    def balance(self, account=None):
        account = account or self.account
        account.refresh_from_db()
        return account.balance_units

    def test_credit_then_debit_tracks_balance_after(self):
        first = wallet.credit(self.account, 1000, LedgerEntry.PURCHASE, 'ord_1')
        second = wallet.debit(self.account, 300, LedgerEntry.USAGE, 's:1')
        self.assertEqual((first.balance_after, second.balance_after), (1000, 700))
        self.assertEqual(second.units, -300)
        self.assertEqual(self.balance(), 700)

    def test_duplicate_reference_is_applied_once(self):
        self.assertIsNotNone(wallet.credit(self.account, 500, LedgerEntry.PURCHASE, 'ord_1'))
        self.assertIsNone(wallet.credit(self.account, 500, LedgerEntry.PURCHASE, 'ord_1'))
        self.assertEqual(self.balance(), 500)
        self.assertEqual(LedgerEntry.objects.count(), 1)

    def test_debit_never_goes_below_zero(self):
        wallet.credit(self.account, 100, LedgerEntry.ADJUSTMENT, 'adj:1')
        entry = wallet.debit(self.account, 250, LedgerEntry.USAGE, 's:1')
        self.assertEqual(entry.units, -100)
        self.assertEqual(entry.details['asked'], 250)
        self.assertEqual(self.balance(), 0)
        again = wallet.debit(self.account, 50, LedgerEntry.USAGE, 's:2')
        self.assertEqual(again.units, 0)
        self.assertEqual(self.balance(), 0)

    def test_usage_units(self):
        self.assertEqual(wallet.usage_units(1000, 0, 0), 12)
        self.assertEqual(wallet.usage_units(500, 500, 0), 12)
        self.assertEqual(wallet.usage_units(1, 0, 0), 1)
        self.assertEqual(wallet.usage_units(60_000, 60_000, 912), 1440 + 4560)

    def test_record_usage_is_idempotent_and_skips_zero(self):
        wallet.credit(self.account, 10_000, LedgerEntry.PURCHASE, 'ord_1')
        self.assertEqual(wallet.record_usage(self.account, 'sess', 1, 1000, 1000, 10), (74, 9926))
        self.assertEqual(wallet.record_usage(self.account, 'sess', 1, 1000, 1000, 10), (0, 9926))
        self.assertEqual(wallet.record_usage(self.account, 'sess', 2, 0, 0, 0), (0, 9926))
        usage = LedgerEntry.objects.filter(kind=LedgerEntry.USAGE)
        self.assertEqual(usage.count(), 1)
        self.assertEqual(usage.get().reference, f'{self.account.pk}:sess:1')
        self.assertEqual(usage.get().details, {'stt_ms_out': 1000, 'stt_ms_in': 1000, 'tts_chars': 10, 'asked': 74})

    def test_the_same_session_id_on_two_accounts_is_charged_twice(self):
        other = make_account(2)
        for account in (self.account, other):
            wallet.credit(account, 1000, LedgerEntry.ADJUSTMENT, f'adj:{account.pk}')
            self.assertEqual(wallet.record_usage(account, 'sess', 1, 1000, 0, 0), (12, 988))

    def test_trial_rules(self):
        self.assertEqual(wallet.grant_trial(self.account, 'device-aaaa', now=NOW), 'granted')
        self.assertEqual(self.balance(), 30_000)
        self.assertEqual(wallet.grant_trial(self.account, 'device-bbbb', now=NOW), 'account_used')
        other = make_account(2)
        self.assertEqual(wallet.grant_trial(other, 'device-aaaa', now=NOW), 'device_used')
        self.assertEqual(self.balance(other), 0)
        self.assertEqual(TrialDevice.objects.get().account, self.account)
        with override_settings(LIVEBRIDGE_TRIALS_PER_DAY=1):
            third = make_account(3)
            self.assertEqual(wallet.grant_trial(third, 'device-cccc', now=NOW), 'daily_cap')
            self.assertEqual(self.balance(third), 0)

    def test_adjust_needs_a_reason(self):
        with self.assertRaises(ValueError):
            wallet.adjust(self.account, 100, '  ', 'staff@x')
        with self.assertRaises(ValueError):
            wallet.adjust(self.account, 0, 'goodwill', 'staff@x')
        self.assertEqual(LedgerEntry.objects.count(), 0)

    def test_adjust_records_who(self):
        entry = wallet.adjust(self.account, 6000, 'goodwill', 'staff@x')
        self.assertEqual(entry.kind, LedgerEntry.ADJUSTMENT)
        self.assertEqual(entry.details, {'reason': 'goodwill', 'by': 'staff@x'})
        self.assertEqual(self.balance(), 6000)
        down = wallet.adjust(self.account, -1000, 'mistake', 'staff@x')
        self.assertEqual((down.units, self.balance()), (-1000, 5000))

    def test_has_purchase(self):
        self.assertFalse(wallet.has_purchase(self.account))
        wallet.grant_trial(self.account, 'device-aaaa', now=NOW)
        self.assertFalse(wallet.has_purchase(self.account))
        wallet.credit(self.account, 360_000, LedgerEntry.PURCHASE, 'ord_1')
        self.assertTrue(wallet.has_purchase(self.account))

    def test_minutes(self):
        self.assertEqual(wallet.minutes(29_000), 4)
        self.assertEqual(wallet.minutes(360_000), 60)
