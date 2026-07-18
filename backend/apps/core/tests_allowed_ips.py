"""
Tests for the shared dynamic admin IP allowlist (core.allowed_ips) and its
integration points: AdminIPRestrictionMiddleware union + the /myip/ echo page.
"""
import json
import os
import tempfile

from core import allowed_ips
from core.allowed_ips import (
    add_ip,
    decode_ip,
    encode_ip,
    get_dynamic_ips,
    load_data,
    normalize_ip,
    remove_ip,
)
from core.security_middleware import AdminIPRestrictionMiddleware
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase, override_settings


class _TmpFileMixin:
    """Route the shared file into a per-test temp path + reset the read cache."""

    def setUp(self):
        super().setUp()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.ips_path = os.path.join(self._tmpdir.name, 'admin_ips.json')
        self._override = override_settings(ADMIN_ALLOWED_IPS_FILE=self.ips_path)
        self._override.enable()
        allowed_ips._cache['key'] = None
        allowed_ips._cache['ips'] = []

    def tearDown(self):
        self._override.disable()
        self._tmpdir.cleanup()
        allowed_ips._cache['key'] = None
        allowed_ips._cache['ips'] = []
        super().tearDown()


class NormalizeIpTest(TestCase):
    def test_valid_ipv4(self):
        self.assertEqual(normalize_ip(' 84.54.12.7 '), '84.54.12.7')

    def test_valid_ipv6_normalized(self):
        self.assertEqual(normalize_ip('2001:0db8::0001'), '2001:db8::1')

    def test_invalid(self):
        self.assertIsNone(normalize_ip('hello'))
        self.assertIsNone(normalize_ip('999.1.1.1'))
        self.assertIsNone(normalize_ip(''))


class EncodeDecodeTest(TestCase):
    def test_roundtrip_ipv4(self):
        self.assertEqual(decode_ip(encode_ip('84.54.12.7')), '84.54.12.7')

    def test_roundtrip_ipv6(self):
        self.assertEqual(decode_ip(encode_ip('2001:db8::1')), '2001:db8::1')

    def test_garbage(self):
        self.assertIsNone(decode_ip('!!not-b64!!'))
        self.assertIsNone(decode_ip(encode_ip('not-an-ip')))


class AllowedIpsFileTest(_TmpFileMixin, TestCase):
    def test_missing_file_fails_open(self):
        self.assertEqual(get_dynamic_ips(), [])

    def test_add_then_read(self):
        ok, res = add_ip('84.54.12.7', label='uy', by=1)
        self.assertTrue(ok)
        self.assertEqual(res, '84.54.12.7')
        self.assertEqual(get_dynamic_ips(), ['84.54.12.7'])
        data = load_data()
        self.assertEqual(data['ips'][0]['label'], 'uy')
        self.assertEqual(data['history'][-1]['op'], 'add')

    def test_add_invalid_rejected(self):
        ok, msg = add_ip('nonsense')
        self.assertFalse(ok)
        self.assertEqual(get_dynamic_ips(), [])

    def test_duplicate_rejected(self):
        add_ip('84.54.12.7')
        ok, _ = add_ip('84.54.12.7')
        self.assertFalse(ok)

    def test_remove(self):
        add_ip('84.54.12.7')
        add_ip('10.1.2.3')
        ok, _ = remove_ip('84.54.12.7', by=2)
        self.assertTrue(ok)
        self.assertEqual(get_dynamic_ips(), ['10.1.2.3'])
        self.assertEqual(load_data()['history'][-1]['op'], 'remove')

    def test_remove_unknown(self):
        ok, _ = remove_ip('8.8.8.8')
        self.assertFalse(ok)

    def test_corrupt_file_fails_open(self):
        with open(self.ips_path, 'w') as fh:
            fh.write('{broken json')
        self.assertEqual(get_dynamic_ips(), [])

    def test_mtime_cache_refreshes_on_change(self):
        add_ip('84.54.12.7')
        self.assertEqual(get_dynamic_ips(), ['84.54.12.7'])
        add_ip('10.1.2.3')
        self.assertEqual(sorted(get_dynamic_ips()), ['10.1.2.3', '84.54.12.7'])

    def test_history_capped(self):
        for i in range(1, 30):
            add_ip(f'10.0.0.{i}')
            remove_ip(f'10.0.0.{i}')
        self.assertLessEqual(len(load_data()['history']), allowed_ips.MAX_HISTORY)

    def test_file_is_world_readable(self):
        add_ip('84.54.12.7')
        mode = os.stat(self.ips_path).st_mode & 0o777
        self.assertEqual(mode, 0o644)

    def test_atomic_write_valid_json(self):
        add_ip('84.54.12.7')
        with open(self.ips_path) as fh:
            data = json.load(fh)
        self.assertEqual(data['version'], 1)


@override_settings(ADMIN_URL_PREFIX='jk-test-admin/', ADMIN_ALLOWED_IPS=['10.0.0.1'])
class AdminGateUnionTest(_TmpFileMixin, TestCase):
    def _run(self, ip):
        request = RequestFactory().get('/jk-test-admin/')
        request.META['HTTP_X_REAL_IP'] = ip
        middleware = AdminIPRestrictionMiddleware(lambda r: HttpResponse('ok'))
        return middleware(request)

    def test_env_base_ip_allowed(self):
        self.assertEqual(self._run('10.0.0.1').status_code, 200)

    def test_unknown_ip_404(self):
        with self.assertRaises(Http404):
            self._run('203.0.113.9')

    def test_dynamic_ip_allowed_without_restart(self):
        with self.assertRaises(Http404):
            self._run('203.0.113.9')
        add_ip('203.0.113.9')  # bot writes the shared file...
        self.assertEqual(self._run('203.0.113.9').status_code, 200)  # ...instant

    def test_removed_dynamic_ip_blocked_again(self):
        add_ip('203.0.113.9')
        self.assertEqual(self._run('203.0.113.9').status_code, 200)
        remove_ip('203.0.113.9')
        with self.assertRaises(Http404):
            self._run('203.0.113.9')

    def test_non_admin_path_untouched(self):
        request = RequestFactory().get('/xo/')
        request.META['HTTP_X_REAL_IP'] = '203.0.113.9'
        middleware = AdminIPRestrictionMiddleware(lambda r: HttpResponse('ok'))
        self.assertEqual(middleware(request).status_code, 200)


class MyIpViewTest(_TmpFileMixin, TestCase):
    def test_echoes_real_ip(self):
        resp = self.client.get('/myip/', HTTP_X_REAL_IP='203.0.113.5')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('203.0.113.5', resp.content.decode())
        self.assertIn('no-store', resp['Cache-Control'])

    @override_settings(TELEGRAM_BOT_USERNAME='TestBot')
    def test_deep_link_present(self):
        resp = self.client.get('/myip/', HTTP_X_REAL_IP='203.0.113.5')
        content = resp.content.decode()
        self.assertIn(f'https://t.me/TestBot?start=addip_{encode_ip("203.0.113.5")}', content)
