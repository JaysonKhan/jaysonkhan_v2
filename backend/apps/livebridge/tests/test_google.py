"""Google sign-in on the web: server-side code exchange with PKCE, its failure paths, and the session."""
import base64
import hashlib
import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

import httpx
from django.contrib.auth import get_user, get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from livebridge import google
from livebridge.models import Account
from livebridge.session import SESSION_KEY

CLIENT_ID = 'test-client.apps.googleusercontent.com'
GOOGLE_ON = override_settings(GOOGLE_OAUTH_CLIENT_ID=CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET='test-secret')


def tokeninfo(**overrides):
    payload = {'iss': 'https://accounts.google.com', 'aud': CLIENT_ID, 'sub': '1234567890',
               'email': 'person@example.com', 'email_verified': 'true', 'name': 'A Person',
               'exp': str(int(time.time()) + 600)}
    payload.update(overrides)
    return httpx.Response(200, json={k: v for k, v in payload.items() if v is not None})


@GOOGLE_ON
class GoogleSignInTest(TestCase):
    def setUp(self):
        cache.clear()
        self.start_url = reverse('livebridge_google_start')
        self.callback_url = reverse('livebridge_google_callback')

    def start(self, next_url=None):
        query = {'next': next_url} if next_url else {}
        response = self.client.get(self.start_url, query)
        self.assertEqual(response.status_code, 302)
        return response

    def callback(self, info=None, state=None, HTTP_ACCEPT_LANGUAGE='en', **query):
        pending = self.client.session.get('lb_google') or {}
        params = {'state': state if state is not None else pending.get('state', ''), 'code': 'auth-code', **query}
        with mock.patch('livebridge.google._post_token',
                        return_value=httpx.Response(200, json={'id_token': 'id-token'})) as post, \
                mock.patch('livebridge.google._tokeninfo_get', return_value=info or tokeninfo()):
            response = self.client.get(self.callback_url, params, HTTP_ACCEPT_LANGUAGE=HTTP_ACCEPT_LANGUAGE)
        return response, post

    def test_start_redirects_with_state_and_pkce(self):
        response = self.start()
        location = urlparse(response['Location'])
        self.assertEqual(location.netloc, 'accounts.google.com')
        query = {k: v[0] for k, v in parse_qs(location.query).items()}
        pending = self.client.session['lb_google']
        self.assertEqual(query['state'], pending['state'])
        expected = base64.urlsafe_b64encode(hashlib.sha256(pending['verifier'].encode()).digest()).rstrip(b'=')
        self.assertEqual(query['code_challenge'], expected.decode())
        self.assertEqual(query['code_challenge_method'], 'S256')
        self.assertEqual(query['redirect_uri'], 'http://testserver' + self.callback_url)
        self.assertEqual(query['client_id'], CLIENT_ID)
        self.assertEqual(query['scope'], 'openid email profile')
        self.assertEqual(query['prompt'], 'select_account')
        self.assertEqual(query['response_type'], 'code')

    @override_settings(GOOGLE_OAUTH_CLIENT_ID='')
    def test_not_configured_means_no_redirect(self):
        response = self.start()
        self.assertTrue(response['Location'].endswith('/account/'))
        self.assertNotIn('lb_google', self.client.session)

    @override_settings(GOOGLE_OAUTH_CLIENT_ID='')
    def test_coming_back_keeps_the_language_of_next(self):
        response = self.client.get(self.start_url, {'next': '/uz/account/connect/?code=BCDF-GHJK'},
                                   HTTP_ACCEPT_LANGUAGE='ru')
        self.assertEqual(response['Location'], '/uz/account/')
        page = self.client.get(response['Location'])
        self.assertContains(page, 'Kirish hali sozlanmagan.')

    def test_cancel_comes_back_in_the_language_of_next(self):
        self.client.get(self.start_url, {'next': '/ru/account/'}, HTTP_ACCEPT_LANGUAGE='en')
        response, _ = self.callback(error='access_denied', HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(response['Location'], '/ru/account/')
        self.assertContains(self.client.get(response['Location']), 'Вход отменён.')

    def test_callback_creates_then_finds_the_account(self):
        account_page = reverse('account')
        self.start(next_url=account_page)
        response, post = self.callback()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], account_page)
        account = Account.objects.get()
        self.assertEqual((account.google_sub, account.email, account.name), ('1234567890', 'person@example.com',
                                                                            'A Person'))
        self.assertEqual(self.client.session[SESSION_KEY], account.pk)
        self.assertNotIn('lb_google', self.client.session)

        self.start()
        self.callback(tokeninfo(email='new@example.com'))
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(Account.objects.get().email, 'new@example.com')

    def test_exchange_sends_the_verifier_and_redirect_uri(self):
        self.start()
        verifier = self.client.session['lb_google']['verifier']
        _, post = self.callback()
        sent = post.call_args.args[0]
        self.assertEqual(sent['code_verifier'], verifier)
        self.assertEqual(sent['code'], 'auth-code')
        self.assertEqual(sent['redirect_uri'], 'http://testserver' + self.callback_url)
        self.assertEqual(sent['grant_type'], 'authorization_code')

    def test_callback_refuses_bad_state_and_old_state(self):
        self.start()
        response, post = self.callback(state='not-the-state')
        self.assertTrue(response['Location'].endswith('/account/'))
        post.assert_not_called()
        self.assertFalse(Account.objects.exists())

        self.start()
        session = self.client.session
        session['lb_google'] = {**session['lb_google'], 'at': time.time() - 601}
        session.save()
        response, post = self.callback()
        self.assertTrue(response['Location'].endswith('/account/'))
        post.assert_not_called()
        self.assertFalse(Account.objects.exists())

        response, post = self.callback(state='')  # no pending sign-in at all
        post.assert_not_called()
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_cancelled_at_google(self):
        self.start()
        response, post = self.callback(error='access_denied')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('/account/'))
        post.assert_not_called()
        self.assertFalse(Account.objects.exists())

    def test_next_cannot_leave_the_site(self):
        for bad in ('https://evil.example/', '//evil.example/', 'javascript:alert(1)', 'account/'):
            with self.subTest(next=bad):
                self.start(next_url=bad)
                self.assertEqual(self.client.session['lb_google']['next'], reverse('account'))
        self.start(next_url='/en/account/connect/?code=BCDF-GHJK')
        self.assertEqual(self.client.session['lb_google']['next'], '/en/account/connect/?code=BCDF-GHJK')

    def test_failed_verification_is_counted_and_limited(self):
        for _ in range(15):
            self.start()
            response, _ = self.callback(tokeninfo(aud='someone-else'))
            self.assertEqual(response.status_code, 302)
        self.start()
        response, _ = self.callback(tokeninfo(aud='someone-else'))
        self.assertEqual(response.status_code, 429)
        self.assertFalse(Account.objects.exists())

    def test_inactive_account_cannot_sign_in(self):
        Account.objects.create(google_sub='1234567890', email='person@example.com', is_active=False)
        self.start()
        self.callback()
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_other_sign_ins_survive(self):
        staff = get_user_model().objects.create_user(username='owner', email='owner@example.com',
                                                     password='secret123', is_staff=True)
        self.client.force_login(staff)
        session = self.client.session
        session['tg_profile_id'] = 42
        session.save()

        self.start()
        self.callback()
        self.assertEqual(self.client.session['tg_profile_id'], 42)
        self.assertEqual(get_user(self.client), staff)
        self.assertIn(SESSION_KEY, self.client.session)

        response = self.client.post(reverse('account_sign_out'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(self.client.session['tg_profile_id'], 42)
        self.assertEqual(get_user(self.client), staff)


@GOOGLE_ON
class VerifyIdTokenTest(TestCase):
    def verify(self, response):
        with mock.patch('livebridge.google._tokeninfo_get', return_value=response):
            return google.verify_id_token('id-token')

    def test_accepts_a_good_token(self):
        self.assertEqual(self.verify(tokeninfo()), {'sub': '1234567890', 'email': 'person@example.com',
                                                    'name': 'A Person'})
        self.assertIsNotNone(self.verify(tokeninfo(iss='accounts.google.com', email_verified=True)))

    def test_verify_rejects_wrong_audience_issuer_and_unverified_email(self):
        for bad in (tokeninfo(aud='someone-else'), tokeninfo(iss='https://evil.example'),
                    tokeninfo(email_verified='false'), tokeninfo(email_verified=None), tokeninfo(sub=None),
                    tokeninfo(exp=str(int(time.time()) - 5)), httpx.Response(400, json={'error': 'invalid_token'})):
            with self.subTest(response=bad):
                self.assertIsNone(self.verify(bad))

    def test_network_error_is_a_refusal(self):
        with mock.patch('livebridge.google._tokeninfo_get', side_effect=httpx.ConnectError('down')):
            self.assertIsNone(google.verify_id_token('id-token'))

    @override_settings(GOOGLE_OAUTH_CLIENT_ID='')
    def test_no_client_id_accepts_nothing(self):
        self.assertIsNone(self.verify(tokeninfo(aud='')))
