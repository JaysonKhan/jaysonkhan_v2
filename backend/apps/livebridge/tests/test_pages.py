"""The account pages: signed out / in, connecting the app with its code, history, devices, deletion."""
from unittest import mock
from urllib.parse import parse_qs, urlparse

from core.models import SiteSettings
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import translation

from livebridge import devices, wallet
from livebridge.models import Account, Device, DeviceGrant
from livebridge.session import SESSION_KEY

LANGS = ('xo', 'uz', 'ru', 'en')
ENGLISH_ONLY = ('Sign in with Google', 'Connected — go back to the app')


def make_account(n=1):
    return Account.objects.create(google_sub=f'sub-{n}', email=f'person{n}@example.com')


def signed_in_client(account, **headers):
    client = Client(**headers)
    session = client.session
    session[SESSION_KEY] = account.pk
    session.save()
    return client


class AccountPagesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def setUp(self):
        cache.clear()
        self.enterContext(translation.override('en'))  # URLs under /en/, so the English copy is asserted
        self.account = make_account()
        self.client = signed_in_client(self.account)

    def connect_url(self, code=None):
        url = reverse('account_connect')
        return f'{url}?code={code}' if code else url

    def test_pages_render_in_every_language(self):
        for lang in LANGS:
            with self.subTest(lang=lang), translation.override(lang):
                grant, _ = devices.start_grant(f'device-{lang}-0001', f'Mac {lang}')
                pages = {
                    'signed out': Client().get(reverse('account')),
                    'signed in': self.client.get(reverse('account')),
                    'connect': self.client.get(self.connect_url(grant.user_code)),
                    'connected': self.client.post(reverse('account_connect'),
                                                  {'code': grant.user_code, 'action': 'connect'}),
                    'purchase done': self.client.get(reverse('account_purchase_done') + '?checkout_id=x'),
                }
                for name, response in pages.items():
                    self.assertEqual(response.status_code, 200, name)
                    html = response.content.decode()
                    self.assertIn('name="robots" content="noindex"', html, name)
                    self.assertIn(f'lang="{lang}"', html, name)
                    if lang != 'en':
                        for english in ENGLISH_ONLY:
                            self.assertNotIn(english, html, f'{name}: {english}')
                self.assertIn(grant.user_code, pages['connect'].content.decode())
                self.assertIn(f'Mac {lang}', pages['connect'].content.decode())
                if lang == 'en':
                    self.assertIn('Sign in with Google', pages['signed out'].content.decode())
                    self.assertIn('Connected — go back to the app', pages['connected'].content.decode())

    def test_connect_requires_sign_in_and_keeps_the_code(self):
        response = Client().get(self.connect_url('BCDF-GHJK'))
        self.assertEqual(response.status_code, 302)
        location = urlparse(response['Location'])
        self.assertEqual(location.path, reverse('livebridge_google_start'))
        next_url = parse_qs(location.query)['next'][0]
        self.assertEqual(urlparse(next_url).path, reverse('account_connect'))
        self.assertIn('?code=BCDF-GHJK', next_url)

    def test_connect_and_cancel(self):
        grant, _ = devices.start_grant('device-0001', 'Work Mac')
        response = self.client.post(reverse('account_connect'), {'code': grant.user_code, 'action': 'connect'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connected — go back to the app')
        self.assertContains(response, '5 free minutes added')
        grant.refresh_from_db()
        self.assertEqual((grant.status, grant.account), (DeviceGrant.APPROVED, self.account))

        other, _ = devices.start_grant('device-0002', 'Home PC')
        response = self.client.post(reverse('account_connect'), {'code': other.user_code, 'action': 'cancel'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Connected — go back to the app')
        other.refresh_from_db()
        self.assertEqual(other.status, DeviceGrant.DENIED)

    def test_connect_without_or_with_a_wrong_code_shows_the_code_field(self):
        response = self.client.get(self.connect_url())
        self.assertContains(response, 'name="code"')
        response = self.client.get(self.connect_url('BCDF-GHJK'))
        self.assertContains(response, 'name="code"')
        self.assertContains(response, 'This code is not valid or has expired.')

    def test_daily_cap_outcome_is_explained(self):
        with self.settings(LIVEBRIDGE_TRIALS_PER_DAY=0):
            grant, _ = devices.start_grant('device-0001', 'Work Mac')
            response = self.client.post(reverse('account_connect'), {'code': grant.user_code, 'action': 'connect'})
        self.assertContains(response, 'Free minutes have run out for today')
        self.assertNotContains(response, 'free minutes added')

    def test_wrong_codes_are_limited(self):
        for _ in range(10):
            response = self.client.get(self.connect_url('BCDF-GHJK'))
            self.assertContains(response, 'This code is not valid or has expired.')
        grant, _ = devices.start_grant('device-0001', 'Work Mac')
        with mock.patch('livebridge.devices.find_pending_grant') as lookup:
            response = self.client.get(self.connect_url(grant.user_code))
            lookup.assert_not_called()
        self.assertContains(response, 'Too many wrong codes.')
        self.assertNotContains(response, 'Work Mac')
        response = self.client.post(reverse('account_connect'), {'code': grant.user_code, 'action': 'connect'})
        self.assertContains(response, 'Too many wrong codes.')
        grant.refresh_from_db()
        self.assertEqual(grant.status, DeviceGrant.PENDING)

    def test_wrong_codes_are_limited_per_address(self):
        headers = {'HTTP_X_REAL_IP': '203.0.113.9'}
        for n in range(2, 5):
            client = signed_in_client(make_account(n), **headers)
            for _ in range(10):
                client.get(self.connect_url('BCDF-GHJK'))
        response = signed_in_client(make_account(5), **headers).get(self.connect_url('BCDF-GHJK'))
        self.assertContains(response, 'Too many wrong codes.')

    def test_device_sign_out_only_for_own_devices(self):
        other = make_account(2)
        theirs = Device.objects.create(account=other, device_id='device-9999', name='Their Mac',
                                       refresh_hash='x' * 64, refresh_expires_at='2030-01-01T00:00Z')
        mine = Device.objects.create(account=self.account, device_id='device-0001', name='My Mac',
                                     refresh_hash='y' * 64, refresh_expires_at='2030-01-01T00:00Z')
        response = self.client.post(reverse('account_device_sign_out', args=[theirs.pk]))
        self.assertEqual(response.status_code, 404)
        theirs.refresh_from_db()
        self.assertIsNone(theirs.revoked_at)
        response = self.client.post(reverse('account_device_sign_out', args=[mine.pk]))
        self.assertEqual(response.status_code, 302)
        mine.refresh_from_db()
        self.assertIsNotNone(mine.revoked_at)
        self.assertEqual(self.client.get(reverse('account_device_sign_out', args=[mine.pk])).status_code, 405)

    def test_delete_request_revokes_and_signs_out(self):
        device = Device.objects.create(account=self.account, device_id='device-0001', name='My Mac',
                                       refresh_hash='y' * 64, refresh_expires_at='2030-01-01T00:00Z')
        self.client.post(reverse('account_delete'))
        self.account.refresh_from_db()
        self.assertIsNone(self.account.deletion_requested_at)
        self.assertIn(SESSION_KEY, self.client.session)

        response = self.client.post(reverse('account_delete'), {'confirm': 'on'}, follow=True)
        self.account.refresh_from_db()
        device.refresh_from_db()
        self.assertIsNotNone(self.account.deletion_requested_at)
        self.assertIsNotNone(device.revoked_at)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(response, 'Your account will be deleted within 30 days.')

    def test_history_and_balance(self):
        wallet.grant_trial(self.account, 'device-0001')
        wallet.record_usage(self.account, 'sess', 1, 0, 0, 200)
        response = self.client.get(reverse('account'))
        self.assertContains(response, '≈ 4 min')
        self.assertContains(response, '29\xa0000')
        self.assertContains(response, 'Free trial')
        self.assertContains(response, 'person1@example.com')
        for code in ('Starter', 'Medium', 'Large'):
            self.assertContains(response, code)

    def test_livebridge_page_links_to_the_account(self):
        account_url = reverse('account')
        response = Client().get(reverse('services_livebridge'))
        self.assertContains(response, f'href="{account_url}"')
        self.assertContains(response, '>Sign in<')
        response = self.client.get(reverse('services_livebridge'))
        self.assertContains(response, 'Your account')

    def test_sign_out_keeps_the_page_reachable(self):
        response = self.client.post(reverse('account_sign_out'), follow=True)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(response, 'Sign in with Google')
