"""Proxy pool: TXT parsing, import rules, the shared file, and the admin import page."""
import json
import os
import stat
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from proxies.models import Proxy
from proxies.services import export_shared, import_proxies, parse_proxy_list

SAMPLE = 'user1:secret@216.26.239.92:3129\nuser1:secret@65.111.5.93:3129\n'


class _PoolFileMixin:
    """Route the shared file into a per-test temp directory."""

    def setUp(self):
        super().setUp()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.pool_path = os.path.join(self._tmpdir.name, 'proxies.json')
        self._override = override_settings(PROXY_POOL_FILE=self.pool_path)
        self._override.enable()

    def tearDown(self):
        self._override.disable()
        self._tmpdir.cleanup()
        super().tearDown()

    def published(self):
        with open(self.pool_path, encoding='utf-8') as fh:
            return json.load(fh)


class ParseTest(TestCase):
    def test_provider_export_format(self):
        entries, invalid = parse_proxy_list(SAMPLE)
        self.assertEqual(invalid, [])
        self.assertEqual(
            [(e.host, e.port, e.username, e.password) for e in entries],
            [('216.26.239.92', 3129, 'user1', 'secret'), ('65.111.5.93', 3129, 'user1', 'secret')],
        )

    def test_optional_scheme_and_missing_credentials(self):
        entries, invalid = parse_proxy_list('http://u:p@proxy.example.com:8080\n10.0.0.1:3128\n')
        self.assertEqual(invalid, [])
        self.assertEqual([(e.host, e.port, e.username) for e in entries],
                         [('proxy.example.com', 8080, 'u'), ('10.0.0.1', 3128, '')])

    def test_blank_and_comment_lines_are_skipped(self):
        entries, invalid = parse_proxy_list('﻿# my list\n\n  u:p@1.2.3.4:80  \n')
        self.assertEqual((len(entries), invalid), (1, []))

    def test_unreadable_lines_are_reported_by_number(self):
        entries, invalid = parse_proxy_list('u:p@1.2.3.4:80\nnot a proxy\nu:p@1.2.3.4:99999\nsocks5://1.2.3.4:1080\n')
        self.assertEqual(len(entries), 1)
        self.assertEqual(invalid, [2, 3, 4])

    def test_repeated_endpoint_keeps_the_last_line(self):
        entries, _ = parse_proxy_list('u:old@1.2.3.4:80\nu:new@1.2.3.4:80\n')
        self.assertEqual([e.password for e in entries], ['new'])


class ImportTest(TestCase):
    def test_creates_then_reimport_changes_nothing(self):
        first = import_proxies(SAMPLE, source='list.txt')
        self.assertEqual((first.created, first.updated, first.unchanged), (2, 0, 0))
        self.assertEqual(set(Proxy.objects.values_list('source', flat=True)), {'list.txt'})

        again = import_proxies(SAMPLE)
        self.assertEqual((again.created, again.updated, again.unchanged), (0, 0, 2))
        self.assertEqual(Proxy.objects.count(), 2)

    def test_known_endpoint_gets_its_password_refreshed(self):
        import_proxies('u:old@1.2.3.4:80\n')
        result = import_proxies('u:new@1.2.3.4:80\n')
        self.assertEqual((result.created, result.updated), (0, 1))
        self.assertEqual(Proxy.objects.get().password, 'new')

    def test_reimport_does_not_switch_a_disabled_proxy_back_on(self):
        import_proxies(SAMPLE)
        Proxy.objects.update(is_active=False)
        import_proxies(SAMPLE)
        self.assertFalse(Proxy.objects.filter(is_active=True).exists())

    def test_replace_deletes_what_the_list_no_longer_has(self):
        import_proxies(SAMPLE)
        result = import_proxies('user1:secret@65.111.5.93:3129\n', replace=True)
        self.assertEqual(result.removed, 1)
        self.assertEqual(list(Proxy.objects.values_list('host', flat=True)), ['65.111.5.93'])

    def test_replace_with_no_readable_line_keeps_the_pool(self):
        import_proxies(SAMPLE)
        result = import_proxies('this is the wrong file\n', replace=True)
        self.assertEqual((result.removed, result.invalid_lines), (0, [1]))
        self.assertEqual(Proxy.objects.count(), 2)


class ExportTest(_PoolFileMixin, TestCase):
    def test_only_active_proxies_are_published(self):
        import_proxies(SAMPLE)
        Proxy.objects.filter(host='65.111.5.93').update(is_active=False)
        self.assertEqual(export_shared(), (True, ''))
        data = self.published()
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['proxies'], ['http://user1:secret@216.26.239.92:3129'])

    def test_file_is_private(self):
        export_shared()
        self.assertEqual(stat.S_IMODE(os.stat(self.pool_path).st_mode), 0o600)

    def test_credentials_are_percent_encoded(self):
        Proxy.objects.create(host='1.2.3.4', port=80, username='a b', password='p@ss:w/rd')
        export_shared()
        self.assertEqual(self.published()['proxies'], ['http://a%20b:p%40ss%3Aw%2Frd@1.2.3.4:80'])

    def test_empty_pool_publishes_an_empty_list(self):
        export_shared()
        self.assertEqual(self.published()['proxies'], [])

    def test_unwritable_target_is_reported_not_raised(self):
        blocker = os.path.join(self._tmpdir.name, 'not-a-dir')
        open(blocker, 'w').close()
        with override_settings(PROXY_POOL_FILE=os.path.join(blocker, 'proxies.json')):
            ok, error = export_shared()
        self.assertFalse(ok)
        self.assertTrue(error)


class AdminImportTest(_PoolFileMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('admin:proxies_proxy_import')
        self.owner = get_user_model().objects.create_user(
            username='owner', email='owner@example.com', password='secret123', is_staff=True, is_superuser=True,
        )

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_page_renders(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Import qilish')

    def test_upload_imports_and_publishes(self):
        self.client.force_login(self.owner)
        upload = SimpleUploadedFile('proxyscrape.txt', (SAMPLE + 'garbage\n').encode(), content_type='text/plain')
        response = self.client.post(self.url, {'file': upload}, follow=True)
        self.assertRedirects(response, reverse('admin:proxies_proxy_changelist'))
        self.assertEqual(Proxy.objects.count(), 2)
        self.assertEqual(len(self.published()['proxies']), 2)
        self.assertContains(response, '2 ta yangi')
        self.assertContains(response, 'qator raqamlari: 3')

    def test_pasted_text_works_without_a_file(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, {'text': SAMPLE})
        self.assertEqual(Proxy.objects.count(), 2)

    def test_empty_submit_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TXT fayl tanlang')
        self.assertFalse(os.path.exists(self.pool_path))

    def test_switching_off_from_the_list_republishes(self):
        import_proxies(SAMPLE)
        self.client.force_login(self.owner)
        ids = list(Proxy.objects.values_list('pk', flat=True))
        self.client.post(reverse('admin:proxies_proxy_changelist'),
                         {'action': 'deactivate', '_selected_action': ids})
        self.assertEqual(self.published()['proxies'], [])

    def test_staff_without_permission_is_refused(self):
        clerk = get_user_model().objects.create_user(
            username='clerk', email='clerk@example.com', password='x', is_staff=True,
        )
        self.client.force_login(clerk)
        self.assertEqual(self.client.get(self.url).status_code, 403)
