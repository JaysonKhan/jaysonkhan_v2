"""Owner side: balance adjustments with a reason, signing devices out, a read-only ledger, and the legal pages."""
from core.models import SiteSettings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import translation

from livebridge import devices, wallet
from livebridge.models import Account, Device, DeviceGrant, LedgerEntry, Package, TrialDevice

LANGS = ('xo', 'uz', 'ru', 'en')


class AdminTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='owner', email='owner@example.com', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.staff)
        self.account = Account.objects.create(google_sub='sub-1', email='person@example.com')

    def connect(self, device_id='device-0001'):
        grant, code = devices.start_grant(device_id, 'Work Mac')
        devices.approve(grant, self.account)
        return devices.poll(code)

    def test_adjust_form_needs_a_reason_and_records_who(self):
        url = reverse('admin:livebridge_account_adjust_balance', args=[self.account.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        for bad in ({'units': '6000', 'reason': ''}, {'units': '6000', 'reason': '   '}, {'units': '0', 'reason': 'x'},
                    {'units': 'lots', 'reason': 'x'}):
            response = self.client.post(url, bad)
            self.assertEqual(response.status_code, 200, bad)
        self.assertFalse(LedgerEntry.objects.exists())

        response = self.client.post(url, {'units': '6000', 'reason': 'goodwill'})
        self.assertRedirects(response, reverse('admin:livebridge_account_change', args=[self.account.pk]),
                             fetch_redirect_response=False)
        entry = LedgerEntry.objects.get()
        self.assertEqual((entry.kind, entry.units), (LedgerEntry.ADJUSTMENT, 6000))
        self.assertEqual(entry.details, {'reason': 'goodwill', 'by': 'owner@example.com'})
        self.client.post(url, {'units': '-1000', 'reason': 'mistake'})
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_units, 5000)

    def test_adjust_needs_change_permission(self):
        viewer = get_user_model().objects.create_user(username='viewer', email='viewer@example.com',
                                                      password='secret123', is_staff=True)
        client = Client()
        client.force_login(viewer)
        url = reverse('admin:livebridge_account_adjust_balance', args=[self.account.pk])
        self.assertIn(client.post(url, {'units': '6000', 'reason': 'x'}).status_code, (302, 403))
        self.assertFalse(LedgerEntry.objects.exists())

    def test_device_sign_out_action_revokes(self):
        pair = self.connect()
        device = Device.objects.get()
        response = self.client.post(reverse('admin:livebridge_device_changelist'),
                                    {'action': 'sign_out', '_selected_action': [device.pk]})
        self.assertEqual(response.status_code, 302)
        device.refresh_from_db()
        self.assertIsNotNone(device.revoked_at)
        self.assertIsNone(devices.authenticate(pair.access_token))

    def test_account_action_signs_out_all_its_devices(self):
        self.connect('device-0001')
        self.connect('device-0002')
        self.client.post(reverse('admin:livebridge_account_changelist'),
                         {'action': 'sign_out_devices', '_selected_action': [self.account.pk]})
        self.assertFalse(Device.objects.filter(revoked_at__isnull=True).exists())

    def test_ledger_entries_cannot_be_changed_or_deleted(self):
        entry = wallet.adjust(self.account, 6000, 'goodwill', 'owner@example.com')
        change = reverse('admin:livebridge_ledgerentry_change', args=[entry.pk])
        self.assertEqual(self.client.get(change).status_code, 200)
        self.client.post(change, {'units': '999999', 'kind': 'purchase'})
        delete = reverse('admin:livebridge_ledgerentry_delete', args=[entry.pk])
        self.assertEqual(self.client.post(delete, {'post': 'yes'}).status_code, 403)
        self.client.post(reverse('admin:livebridge_ledgerentry_changelist'),
                         {'action': 'delete_selected', '_selected_action': [entry.pk], 'post': 'yes'})
        entry.refresh_from_db()
        self.assertEqual((entry.units, entry.kind), (6000, LedgerEntry.ADJUSTMENT))
        self.assertEqual(self.client.get(reverse('admin:livebridge_ledgerentry_add')).status_code, 403)

    def test_balance_is_not_editable_in_the_account_form(self):
        change = reverse('admin:livebridge_account_change', args=[self.account.pk])
        self.client.post(change, {'balance_units': '999999', 'is_active': 'on'})
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance_units, 0)

    def test_admin_pages_render(self):
        self.connect()
        wallet.adjust(self.account, 6000, 'goodwill', 'owner@example.com')
        for model in (Account, Device, DeviceGrant, TrialDevice, Package, LedgerEntry):
            name = model._meta.model_name
            with self.subTest(model=name):
                self.assertEqual(self.client.get(reverse(f'admin:livebridge_{name}_changelist')).status_code, 200)
                obj = model.objects.first()
                self.assertEqual(self.client.get(reverse(f'admin:livebridge_{name}_change', args=[obj.pk])).status_code,
                                 200)


class LegalPagesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def test_legal_pages_render_in_every_language(self):
        headings = {'livebridge_terms': 'Terms of service', 'livebridge_privacy': 'Privacy policy',
                    'livebridge_refunds': 'Refund policy'}
        for lang in LANGS:
            for name, heading in headings.items():
                with self.subTest(lang=lang, page=name), translation.override(lang):
                    response = self.client.get(reverse(name))
                    self.assertEqual(response.status_code, 200)
                    html = response.content.decode()
                    self.assertIn(heading, html)  # the English text is the binding one
                    self.assertIn('name="robots" content="noindex"', html)
                    if lang == 'en':
                        self.assertIn('Draft — not yet approved', html)
                    else:
                        self.assertNotIn('Draft — not yet approved', html)
                        self.assertNotIn('The English text is the binding version.', html)

    def test_terms_and_account_page_show_the_current_prices(self):
        with translation.override('en'):
            terms = self.client.get(reverse('livebridge_terms')).content.decode()
            signed_in = Client()
            session = signed_in.session
            session['lb_account'] = Account.objects.create(google_sub='sub-9', email='p@example.com').pk
            session.save()
            account = signed_in.get(reverse('account')).content.decode()
        for package in Package.objects.filter(is_active=True):
            price = f'${package.price_cents / 100:g}'
            self.assertIn(f'{price},', terms)
            self.assertIn(f'>{price}<', account)
        self.assertIn('Sales tax or VAT is added at checkout where it applies.', account)

    def test_account_page_links_to_the_legal_pages(self):
        with translation.override('en'):
            html = self.client.get(reverse('account')).content.decode()
            for name in ('livebridge_terms', 'livebridge_privacy', 'livebridge_refunds'):
                self.assertIn(f'href="{reverse(name)}"', html)
