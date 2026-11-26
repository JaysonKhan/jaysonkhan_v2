"""The desktop app's API (/api/livebridge/v1/) and the Polar checkout."""
import json
from unittest import mock

import httpx
from core.models import SiteSettings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from livebridge import devices
from livebridge.models import Account, DeviceGrant, Package
from livebridge.session import SESSION_KEY

API = '/api/livebridge/v1/'
POLAR_ON = override_settings(POLAR_ACCESS_TOKEN='polar_test_token', POLAR_API_BASE='https://sandbox-api.polar.sh')
CHECKOUT_URL = 'https://sandbox.polar.sh/checkout/polar_c_test'


def make_account(n=1):
    return Account.objects.create(google_sub=f'sub-{n}', email=f'person{n}@example.com', name=f'Person {n}')


def issue_tokens(account, device_id='device-0001'):
    grant, code = devices.start_grant(device_id, 'Work Mac')
    devices.approve(grant, account)
    return devices.poll(code)


def polar_answer(status=201, body=None):
    return httpx.Response(status, json=body if body is not None else {'id': 'polar_c_test', 'url': CHECKOUT_URL})


class ApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def setUp(self):
        cache.clear()
        self.account = make_account()

    def call(self, method, path, body=None, token=None, raw=None, **extra):
        if token:
            extra['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        if method == 'get':
            return self.client.get(API + path, **extra)
        data = raw if raw is not None else json.dumps(body if body is not None else {})
        return self.client.post(API + path, data=data, content_type='application/json', **extra)


class DeviceApiTest(ApiTestCase):
    def test_full_device_flow_over_http(self):
        started = self.call('post', 'device/start/', {'device_id': 'device-0001', 'device_name': 'Work Mac'})
        self.assertEqual(started.status_code, 201)
        body = started.json()
        self.assertEqual(set(body), {'device_code', 'user_code', 'verification_uri', 'verification_uri_complete',
                                     'expires_in', 'interval'})
        self.assertEqual(body['verification_uri'], 'http://testserver/en/account/connect/')
        self.assertEqual(body['verification_uri_complete'], f"{body['verification_uri']}?code={body['user_code']}")
        self.assertEqual((body['expires_in'], body['interval']), (600, 5))

        pending = self.call('post', 'device/token/', {'device_code': body['device_code']})
        self.assertEqual((pending.status_code, pending.json()), (400, {'error': 'authorization_pending'}))

        browser = Client()
        session = browser.session
        session[SESSION_KEY] = self.account.pk
        session.save()
        with translation.override('en'):
            connect_url = reverse('account_connect')
        self.assertEqual(browser.post(connect_url, {'code': body['user_code'], 'action': 'connect'}).status_code, 200)

        tokens = self.call('post', 'device/token/', {'device_code': body['device_code']})
        self.assertEqual(tokens.status_code, 200)
        pair = tokens.json()
        self.assertEqual(set(pair), {'access_token', 'refresh_token', 'token_type', 'expires_in'})
        self.assertEqual((pair['token_type'], pair['expires_in']), ('Bearer', 900))

        me = self.call('get', 'me/', token=pair['access_token'])
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json(), {
            'account_id': str(self.account.public_id), 'email': 'person1@example.com', 'name': 'Person 1',
            'balance_units': 30_000, 'units_per_minute': 6000,
            'rates': {'stt_units_per_second': 12, 'tts_units_per_char': 5}, 'has_purchase': False,
        })

        refreshed = self.call('post', 'token/refresh/', {'refresh_token': pair['refresh_token']})
        self.assertEqual(refreshed.status_code, 200)
        new = refreshed.json()
        self.assertEqual(self.call('get', 'me/', token=pair['access_token']).status_code, 401)
        self.assertEqual(self.call('get', 'me/', token=new['access_token']).status_code, 200)

        self.assertEqual(self.call('post', 'logout/', token=new['access_token']).status_code, 204)
        gone = self.call('get', 'me/', token=new['access_token'])
        self.assertEqual((gone.status_code, gone.json()), (401, {'error': 'invalid_token'}))

    def test_token_errors_follow_poll(self):
        unknown = self.call('post', 'device/token/', {'device_code': 'lbd_unknown'})
        self.assertEqual((unknown.status_code, unknown.json()), (400, {'error': 'invalid_grant'}))
        self.assertEqual(self.call('post', 'device/token/', {}).json(), {'error': 'invalid_grant'})
        self.assertEqual(self.call('post', 'device/token/', {'device_code': 5}).json(), {'error': 'invalid_grant'})
        grant, code = devices.start_grant('device-0001', 'Mac')
        devices.deny(grant)
        denied = self.call('post', 'device/token/', {'device_code': code})
        self.assertEqual((denied.status_code, denied.json()), (400, {'error': 'access_denied'}))
        bad = self.call('post', 'device/token/', raw='{not json')
        self.assertEqual((bad.status_code, bad.json()), (400, {'error': 'bad_json'}))

    def test_start_validates_and_limits(self):
        for body in ({'device_id': 'short'}, {'device_id': 'device-0001', 'device_name': 7}, {}, {'device_id': 99}):
            response = self.call('post', 'device/start/', body)
            self.assertEqual((response.status_code, response.json()), (400, {'error': 'invalid_device'}), body)
        no_name = self.call('post', 'device/start/', {'device_id': 'device-0001'})
        self.assertEqual(no_name.status_code, 201)
        self.assertEqual(DeviceGrant.objects.get().device_name, 'LiveBridge')
        for _ in range(15):
            self.assertEqual(self.call('post', 'device/start/', {'device_id': 'device-0001'}).status_code, 201)
        limited = self.call('post', 'device/start/', {'device_id': 'device-0001'})
        self.assertEqual((limited.status_code, limited.json()), (429, {'error': 'rate_limited'}))
        self.assertTrue(int(limited['Retry-After']) > 0)

    def test_refresh_errors(self):
        response = self.call('post', 'token/refresh/', {'refresh_token': 'lbr_unknown'})
        self.assertEqual((response.status_code, response.json()), (401, {'error': 'invalid_grant'}))
        self.assertEqual(self.call('post', 'token/refresh/', {}).status_code, 401)

    def test_bearer_is_required(self):
        pair = issue_tokens(self.account)
        for headers in ({}, {'HTTP_AUTHORIZATION': pair.access_token}, {'HTTP_AUTHORIZATION': 'Basic abc'},
                        {'HTTP_AUTHORIZATION': 'Bearer lba_wrong'}):
            for method, path in (('get', 'me/'), ('post', 'logout/'), ('post', 'checkout/')):
                response = self.call(method, path, **headers)
                self.assertEqual((response.status_code, response.json()), (401, {'error': 'invalid_token'}))
        self.assertEqual(self.call('get', 'me/', HTTP_AUTHORIZATION=f'bearer {pair.access_token}').status_code, 200)

    def test_packages_are_public_and_ordered(self):
        response = self.call('get', 'packages/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {'code': 'starter', 'price_cents': 600, 'currency': 'usd', 'units': 270_000, 'minutes': 45},
            {'code': 'medium', 'price_cents': 1700, 'currency': 'usd', 'units': 1_140_000, 'minutes': 190},
            {'code': 'large', 'price_cents': 4500, 'currency': 'usd', 'units': 3_600_000, 'minutes': 600},
        ])
        Package.objects.filter(code='medium').update(is_active=False)
        self.assertEqual([p['code'] for p in self.call('get', 'packages/').json()], ['starter', 'large'])


@POLAR_ON
class CheckoutTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        Package.objects.filter(code='starter').update(polar_product_id='polar_prod_starter')
        self.pair = issue_tokens(self.account)

    def checkout(self, package='starter', answer=None, **extra):
        side_effect = answer if isinstance(answer, Exception) else None
        with mock.patch('livebridge.polar._post', return_value=answer or polar_answer(),
                        side_effect=side_effect) as post:
            response = self.call('post', 'checkout/', {'package': package}, token=self.pair.access_token, **extra)
        return response, post

    def test_checkout_sends_the_account_and_package(self):
        response, post = self.checkout(HTTP_ACCEPT_LANGUAGE='uz')
        self.assertEqual((response.status_code, response.json()), (201, {'url': CHECKOUT_URL}))
        url, payload, headers = post.call_args.args
        self.assertEqual(url, 'https://sandbox-api.polar.sh/v1/checkouts/')
        self.assertEqual(headers['Authorization'], 'Bearer polar_test_token')
        self.assertEqual(payload, {
            'products': ['polar_prod_starter'],
            'external_customer_id': str(self.account.public_id),
            'customer_email': 'person1@example.com',
            'success_url': 'http://testserver/uz/account/purchase/done/?checkout_id={CHECKOUT_ID}',
            'metadata': {'account': str(self.account.public_id), 'package': 'starter'},
        })

    def test_checkout_unavailable_cases(self):
        cases = [
            ('polar 500', 'starter', polar_answer(500, {'detail': 'boom'})),
            ('no url', 'starter', polar_answer(201, {'id': 'x'})),
            ('network', 'starter', httpx.ConnectError('down')),
            ('no product id', 'medium', None),
        ]
        for name, package, answer in cases:
            with self.subTest(name):
                response, _ = self.checkout(package, answer)
                self.assertEqual((response.status_code, response.json()), (503, {'error': 'checkout_unavailable'}))
        with override_settings(POLAR_ACCESS_TOKEN=''):
            response, post = self.checkout()
            self.assertEqual(response.status_code, 503)
            post.assert_not_called()

    def test_checkouts_are_limited_per_account(self):
        for _ in range(10):
            self.assertEqual(self.checkout()[0].status_code, 201)
        response, post = self.checkout()
        self.assertEqual((response.status_code, response.json()), (429, {'error': 'rate_limited'}))
        post.assert_not_called()
        browser = Client()
        session = browser.session
        session[SESSION_KEY] = self.account.pk
        session.save()
        with translation.override('en'), mock.patch('livebridge.polar._post', return_value=polar_answer()) as post:
            response = browser.get(reverse('account_buy', args=['starter']), follow=True)
            post.assert_not_called()
        self.assertContains(response, 'Too many checkouts. Please try again in an hour.')

    def test_unknown_or_inactive_package(self):
        response, post = self.checkout('platinum')
        self.assertEqual((response.status_code, response.json()), (404, {'error': 'unknown_package'}))
        Package.objects.filter(code='starter').update(is_active=False)
        response, post = self.checkout('starter')
        self.assertEqual(response.status_code, 404)
        post.assert_not_called()

    def test_buy_link_redirects_to_polar(self):
        browser = Client()
        session = browser.session
        session[SESSION_KEY] = self.account.pk
        session.save()
        with translation.override('en'):
            buy_url = reverse('account_buy', args=['starter'])
            account_url = reverse('account')
            self.assertContains(browser.get(account_url), f'href="{buy_url}"')
        with mock.patch('livebridge.polar._post', return_value=polar_answer()):
            response = browser.get(buy_url)
        self.assertEqual((response.status_code, response['Location']), (302, CHECKOUT_URL))

        with mock.patch('livebridge.polar._post', return_value=polar_answer(500, {})):
            response = browser.get(buy_url, follow=True)
        self.assertEqual(response.redirect_chain[-1][0], account_url)
        self.assertContains(response, 'Payment is not available right now.')

        self.assertEqual(browser.get(reverse('account_buy', args=['platinum'])).status_code, 404)
        signed_out = Client().get(buy_url)
        self.assertTrue(signed_out['Location'].startswith(reverse('livebridge_google_start')))
