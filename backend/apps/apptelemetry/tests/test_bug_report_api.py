"""POST /api/services/v1/bug-reports/ — a LiveBridge problem report with its diagnostic log."""
import uuid
from unittest import mock

from apptelemetry.models import AppBugReport, AppInstall

from .helpers import BUG_REPORT_URL, FEEDBACK_URL, ServicesTestCase, turn

DEVICES = {
    'mic': {'name': 'Headset (AirPods Hands-Free)', 'transport': 'bluetooth', 'sampleRate': 16000,
            'inputChannels': 1, 'outputChannels': 0, 'isDefaultInput': True, 'isDefaultOutput': False},
    'headphones': {'name': 'Speakers (Realtek(R) Audio)', 'transport': 'other', 'sampleRate': 48000,
                   'inputChannels': 0, 'outputChannels': 2, 'isDefaultInput': False, 'isDefaultOutput': True},
    'virtualMic': None,
    'sources': ['Zoom.exe'],
    'mode': 'incoming',
    'myLang': 'uz',
    'targetLang': 'en',
    'outCommit': 'manual',
}

LOG = '=== LiveBridge run started 2026-11-27T10:00:00.000+05:00\n10:00:01.000 state     connecting\n'


def report(**extra):
    body = {'app': 'livebridge', 'app_version': '1.2.1+4', 'os_version': 'Windows 11 (build 26100)',
            'platform': 'windows_x64', 'ui_language': 'uz', 'connection_mode': 'account',
            'message': "AirPods'da tarjima eshitilmayapti, noutbuk karnayidan chiqyapti.",
            'devices': DEVICES, 'log': LOG}
    body.update(extra)
    return body


class BugReportApiTest(ServicesTestCase):
    def assertError(self, response, code, status=400):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.json(), {'error': code})

    def test_happy_path_stores_everything_and_links_a_known_install(self):
        install_id = str(uuid.uuid4())
        self.send([turn()], install_id)
        with mock.patch('apptelemetry.services._notify_owner_bug_report') as notify:
            response = self.post_json(BUG_REPORT_URL, report(install_id=install_id, email='a@example.com'))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'ok': True})
        row = AppBugReport.objects.get()
        self.assertEqual(
            (row.app, row.email, row.app_version, row.os_version, row.platform, row.ui_language, row.connection_mode),
            ('livebridge', 'a@example.com', '1.2.1+4', 'Windows 11 (build 26100)', 'windows_x64', 'uz', 'account'),
        )
        self.assertEqual(row.message, report()['message'])
        self.assertEqual(row.device_info, DEVICES)
        self.assertEqual(row.log, LOG)
        self.assertEqual(row.install, AppInstall.objects.get(install_id=install_id))
        notify.assert_called_once_with(row)

    def test_minimal_report(self):
        response = self.post_json(BUG_REPORT_URL, {'app': 'livebridge', 'message': 'ovoz yo‘q'})
        self.assertEqual(response.status_code, 201)
        row = AppBugReport.objects.get()
        self.assertEqual((row.email, row.log, row.device_info, row.install, row.connection_mode),
                         ('', '', {}, None, ''))

    def test_message_rules(self):
        self.assertError(self.post_json(BUG_REPORT_URL, report(message=None)), 'bad_message')
        self.assertError(self.post_json(BUG_REPORT_URL, {'app': 'livebridge'}), 'bad_message')
        self.assertError(self.post_json(BUG_REPORT_URL, report(message='  ')), 'bad_message')
        self.assertError(self.post_json(BUG_REPORT_URL, report(message='x' * 2001)), 'bad_message')
        self.assertEqual(self.post_json(BUG_REPORT_URL, report(message='x' * 2000)).status_code, 201)

    def test_envelope_rules(self):
        self.assertError(self.post_json(BUG_REPORT_URL, 'nope'), 'bad_json')
        self.assertError(self.post_json(BUG_REPORT_URL, '{broken'), 'bad_json')
        self.assertError(self.post_json(BUG_REPORT_URL, report(app='other')), 'unknown_app')
        self.assertError(self.post_json(BUG_REPORT_URL, report(install_id='123')), 'bad_install_id')
        self.assertError(self.post_json(BUG_REPORT_URL, report(email='not-an-email')), 'bad_email')
        self.assertEqual(AppBugReport.objects.count(), 0)

    def test_devices_must_be_a_small_object(self):
        self.assertError(self.post_json(BUG_REPORT_URL, report(devices=[1])), 'bad_devices')
        self.assertError(self.post_json(BUG_REPORT_URL, report(devices='mic')), 'bad_devices')
        big = {'devices': [{'name': 'x' * 100}] * 200}  # ~22 KB encoded
        self.assertError(self.post_json(BUG_REPORT_URL, report(devices=big)), 'bad_devices')
        self.assertEqual(self.post_json(BUG_REPORT_URL, report(devices=None)).status_code, 201)

    def test_log_rules(self):
        self.assertError(self.post_json(BUG_REPORT_URL, report(log=42)), 'bad_log')
        self.assertError(self.post_json(BUG_REPORT_URL, report(log='y' * (257 * 1024))), 'bad_log')
        too_big = report(log='z' * (200 * 1024), message='m', devices={'pad': 'p' * (130 * 1024)})
        self.assertError(self.post_json(BUG_REPORT_URL, too_big), 'too_large', status=413)
        self.assertEqual(AppBugReport.objects.count(), 0)

    def test_unknown_connection_mode_and_long_strings_are_blanked(self):
        self.post_json(BUG_REPORT_URL, report(connection_mode='weird', platform='p' * 40, ui_language='de'))
        row = AppBugReport.objects.get()
        self.assertEqual((row.connection_mode, row.platform, row.ui_language), ('', '', ''))

    def test_rate_limit_is_five_per_address_per_hour(self):
        for _ in range(5):
            self.assertEqual(self.post_json(BUG_REPORT_URL, report()).status_code, 201)
        response = self.post_json(BUG_REPORT_URL, report())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {'error': 'rate_limited'})
        self.assertTrue(int(response['Retry-After']) > 0)
        self.assertEqual(self.post_json(BUG_REPORT_URL, report(), ip='198.51.100.9').status_code, 201)
        feedback = {'app': 'livebridge', 'message': 'ok'}
        self.assertEqual(self.post_json(FEEDBACK_URL, feedback).status_code, 201)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(BUG_REPORT_URL).status_code, 405)
