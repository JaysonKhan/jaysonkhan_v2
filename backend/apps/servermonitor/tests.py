"""
Tests for the v2 owner-bot surface: /ip handlers (with a fake Telegram API),
control-panel command wiring, and the new formatters. No network, no systemd.
"""
import os
import tempfile
from unittest.mock import patch

from core import allowed_ips
from core.allowed_ips import add_ip, encode_ip, load_data
from django.test import TestCase, override_settings

from servermonitor.formatters import (
    format_db_report,
    format_error_scan,
    format_ssl_checks,
    format_web_checks,
)
from servermonitor.handlers import _RESTARTABLE_UNITS, SERVER_COMMANDS, handle_server_callback
from servermonitor.ip_handlers import (
    handle_ip_command,
    handle_start_payload,
    maybe_offer_ip_add,
)
from servermonitor.metrics import MONITORED_SERVICES
from servermonitor.web_checks import ErrorScan, HttpCheck, SslCheck


class FakeAPI:
    """Captures outgoing Telegram calls instead of hitting the network."""

    def __init__(self):
        self.sent = []
        self.answered = []
        self.edited = []
        self.actions = []

    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))
        return {'ok': True, 'result': {'message_id': len(self.sent)}}

    def answer_callback_query(self, cb_id, text=''):
        self.answered.append((cb_id, text))
        return {'ok': True}

    def edit_message_text(self, **kwargs):
        self.edited.append(kwargs)
        return {'ok': True}

    def edit_message_reply_markup(self, **kwargs):
        return {'ok': True}

    def send_chat_action(self, chat_id, action='typing'):
        self.actions.append((chat_id, action))


class _TmpFileMixin:
    def setUp(self):
        super().setUp()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.ips_path = os.path.join(self._tmpdir.name, 'admin_ips.json')
        self._override = override_settings(ADMIN_ALLOWED_IPS_FILE=self.ips_path)
        self._override.enable()
        allowed_ips._cache['key'] = None
        allowed_ips._cache['ips'] = []
        self.api = FakeAPI()

    def tearDown(self):
        self._override.disable()
        self._tmpdir.cleanup()
        super().tearDown()


def _cq(data, tg_id=777):
    return {
        'id': 'cb1',
        'data': data,
        'from': {'id': tg_id},
        'message': {'message_id': 5, 'chat': {'id': tg_id}},
    }


@patch('servermonitor.handlers.is_owner', return_value=True)
class IpHandlersTest(_TmpFileMixin, TestCase):
    def test_ip_panel_sent(self, _owner):
        handled = handle_ip_command(
            '/ip', {'from': {'id': 777}, 'text': '/ip'}, self.api,
        )
        self.assertTrue(handled)
        self.assertIn('Admin IP Allowlist', self.api.sent[0][1])

    def test_ip_add_command_asks_confirm_then_writes(self, _owner):
        handle_ip_command(
            '/ip', {'from': {'id': 777}, 'text': '/ip add 84.54.12.7 uy'}, self.api,
        )
        # Confirm prompt with the encoded callback, nothing written yet.
        self.assertEqual(load_data()['ips'], [])
        markup = self.api.sent[0][2]['reply_markup']
        confirm_cb = markup['inline_keyboard'][0][0]['callback_data']
        self.assertEqual(confirm_cb, f'ipaok_{encode_ip("84.54.12.7")}')

        from servermonitor.ip_handlers import handle_ip_callback
        self.assertTrue(handle_ip_callback(confirm_cb, _cq(confirm_cb), self.api))
        self.assertEqual(load_data()['ips'][0]['ip'], '84.54.12.7')

    def test_bare_ip_text_offers_add(self, _owner):
        offered = maybe_offer_ip_add({'from': {'id': 777}, 'text': ' 10.20.30.40 '}, self.api)
        self.assertTrue(offered)
        self.assertIn('10.20.30.40', self.api.sent[0][1])

    def test_non_ip_text_ignored(self, _owner):
        self.assertFalse(maybe_offer_ip_add({'from': {'id': 777}, 'text': 'salom'}, self.api))
        self.assertEqual(self.api.sent, [])

    def test_deep_link_payload(self, _owner):
        token = encode_ip('203.0.113.7')
        self.assertTrue(handle_start_payload(f'addip_{token}', 777, self.api))
        self.assertIn('203.0.113.7', self.api.sent[0][1])

    def test_delete_flow(self, _owner):
        add_ip('84.54.12.7')
        from servermonitor.ip_handlers import handle_ip_callback
        token = encode_ip('84.54.12.7')
        handle_ip_callback(f'ipdok_{token}', _cq(f'ipdok_{token}'), self.api)
        self.assertEqual(load_data()['ips'], [])

    def test_non_owner_callback_blocked(self, owner_mock):
        owner_mock.return_value = False
        from servermonitor.ip_handlers import handle_ip_callback
        token = encode_ip('84.54.12.7')
        self.assertTrue(handle_ip_callback(f'ipaok_{token}', _cq(f'ipaok_{token}'), self.api))
        self.assertEqual(load_data()['ips'], [])  # write refused
        self.assertIn('owner', self.api.answered[0][1].lower())


@patch('servermonitor.handlers.is_owner', return_value=True)
class PanelAndRestartTest(_TmpFileMixin, TestCase):
    def test_panel_callback_routes_to_ip_panel(self, _owner):
        handled = handle_server_callback('pnl_ip', _cq('pnl_ip'), self.api)
        self.assertTrue(handled)
        self.assertIn('Admin IP Allowlist', self.api.sent[0][1])

    def test_restart_requires_confirm(self, _owner):
        handled = handle_server_callback('rst_jaysonkhan', _cq('rst_jaysonkhan'), self.api)
        self.assertTrue(handled)
        text = self.api.sent[0][1]
        self.assertIn('jaysonkhan', text)
        markup = self.api.sent[0][2]['reply_markup']
        self.assertEqual(
            markup['inline_keyboard'][0][0]['callback_data'], 'rstok_jaysonkhan',
        )

    def test_restart_unknown_unit_rejected(self, _owner):
        handle_server_callback('rstok_evil-unit', _cq('rstok_evil-unit'), self.api)
        self.assertIn('Noma', self.api.answered[0][1])

    def test_restart_cancel(self, _owner):
        self.assertTrue(handle_server_callback('rst_cancel', _cq('rst_cancel'), self.api))

    def test_edustats_bot_confirm_carries_uzbmb_warning(self, _owner):
        handle_server_callback('rst_edustats-bot', _cq('rst_edustats-bot'), self.api)
        self.assertIn('uzbmb', self.api.sent[0][1])


class InventoryTest(TestCase):
    def test_vaygo_monitored(self):
        units = {c['unit'] for c in MONITORED_SERVICES}
        self.assertIn('vaygo-web', units)
        self.assertIn('vaygo-bot', units)

    def test_restartable_is_apps_plus_nginx(self):
        self.assertIn('nginx', _RESTARTABLE_UNITS)
        self.assertNotIn('postgresql@16-main', _RESTARTABLE_UNITS)
        self.assertNotIn('redis-server', _RESTARTABLE_UNITS)

    def test_v2_commands_registered(self):
        for cmd in ('/panel', '/ip', '/web', '/ssl', '/errors', '/top', '/db', '/restart'):
            self.assertIn(cmd, SERVER_COMMANDS)


class FormatterSmokeTest(TestCase):
    def test_web_checks(self):
        text = format_web_checks([
            HttpCheck('jaysonkhan.com', 'https://x/', 200, 120),
            HttpCheck('uzexam.uz', 'https://y/', 0, 8000, error='timeout'),
            HttpCheck('edustats bot API', 'http://127.0.0.1:8433/', 200, 12, internal=True),
        ])
        self.assertIn('jaysonkhan.com', text)
        self.assertIn('ulanish yo', text)
        self.assertIn('Ichki API', text)

    def test_ssl_checks(self):
        text = format_ssl_checks([
            SslCheck('jaysonkhan.com', 55, '2026-09-11'),
            SslCheck('uzexam.uz', 5, '2026-07-23'),
            SslCheck('vaygo.uz', -1, '', error='timeout'),
        ])
        self.assertIn('55 kun', text)
        self.assertIn('5 kun qoldi!', text)

    def test_error_scan(self):
        text = format_error_scan([
            ErrorScan('jaysonkhan', 0),
            ErrorScan('uzexam', 42, sample='ValueError: boom <tag>'),
        ], hours=6)
        self.assertIn('42 ta', text)
        self.assertIn('&lt;tag&gt;', text)  # sample is HTML-escaped

    def test_db_report(self):
        text = format_db_report(
            [{'name': 'uzexam_db', 'size': '1200 MB'}], 17, '',
        )
        self.assertIn('uzexam_db', text)
        self.assertIn('17', text)
        err_text = format_db_report([], 0, 'psql xato')
        self.assertIn('psql xato', err_text)
