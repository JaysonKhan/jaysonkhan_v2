"""LiveBridge account models: seeded packages and the uniqueness rules the wallet relies on."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from livebridge.models import Account, LedgerEntry, Package


def make_account(sub='sub-1', email='a@example.com'):
    return Account.objects.create(google_sub=sub, email=email)


class ModelsTest(TestCase):
    def test_packages_are_seeded(self):
        rows = list(Package.objects.order_by('sort_order').values_list('code', 'price_cents', 'units'))
        self.assertEqual(rows, [('starter', 500, 360_000), ('medium', 1500, 1_200_000), ('large', 4000, 3_600_000)])
        self.assertTrue(all(p.is_active and p.polar_product_id == '' for p in Package.objects.all()))

    def test_google_sub_is_unique(self):
        make_account()
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_account(email='other@example.com')

    def test_ledger_reference_is_unique_per_kind(self):
        account = make_account()

        def entry(kind, reference):
            return LedgerEntry.objects.create(account=account, kind=kind, units=1, balance_after=1,
                                              reference=reference)

        entry(LedgerEntry.PURCHASE, 'ord_1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            entry(LedgerEntry.PURCHASE, 'ord_1')
        entry(LedgerEntry.REFUND, 'ord_1')
        entry(LedgerEntry.USAGE, '')
        entry(LedgerEntry.USAGE, '')
        self.assertEqual(LedgerEntry.objects.count(), 4)
