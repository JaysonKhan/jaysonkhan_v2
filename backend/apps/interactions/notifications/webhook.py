"""
Telegram Bot webhook receiver.

Handles:
- Private chat: /start, /lang, /notifications (inline keyboard toggles)
- Admin group:  /ban, /mute (reply to logged message), /config
- Callback queries for inline keyboard presses

All user-visible texts render via core.bot_i18n (uz/ru); the language is
resolved per chat (explicit /lang pref → Telegram client language → uz).
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import timedelta
from typing import Optional

from core.bot_i18n import t
from core.emoji import ce
from core.services import SiteSettingsService
from django.conf import settings
from django.db import connections
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from interactions.models import (
    AdminLogMessage,
    NotificationPreference,
    UserBan,
)
from servermonitor.handlers import handle_server_callback, handle_server_command
from telegram.models import TelegramEntity

from .emoji_admin import handle_emoji_input
from .lang import resolve_lang, set_lang
from .telegram_api import TelegramBotAPI

logger = logging.getLogger('interactions.notifications')

MUTE_DAYS = 3

# ── Config field mapping (callback_data → SiteSettings field name) ────────────
CONFIG_FIELDS = {
    'cfg_new_users': 'admin_notify_new_users',
    'cfg_comments': 'admin_notify_comments',
    'cfg_replies': 'admin_notify_replies',
    'cfg_reactions': 'admin_notify_reactions',
    'cfg_likes': 'admin_notify_likes',
    'cfg_contacts': 'admin_notify_contacts',
}

# /start owner menu layout: section key → [(command, emoji), ...].
# Descriptions come from the same cmd.* catalogue keys BotFather uses.
_START_MENU = (
    ('start.sec_manage', (
        ('panel', ('server', '🎛')),
        ('ip', ('lock', '🛡')),
        ('restart', ('swap', '🔄')),
    )),
    ('start.sec_monitoring', (
        ('status', ('chart', '📊')),
        ('services', ('services_icon', '🔧')),
        ('web', ('web', '🌐')),
        ('ssl', ('lock', '🔐')),
        ('errors', ('logs_icon', '🧾')),
        ('disk', ('disk', '💿')),
        ('top', ('trophy', '🏆')),
        ('db', (None, '🐘')),
        ('tariff', ('money', '💰')),
        ('logs', ('logs_icon', '📋')),
        ('backup', ('backup_icon', '💾')),
    )),
    ('start.sec_settings', (
        ('notifications', ('notifications_icon', '🔔')),
        ('config', ('config_icon', '⚙️')),
        ('lang', (None, '🌐')),
    )),
)

_LANG_BUTTONS = {'inline_keyboard': [[
    {'text': "🇺🇿 O'zbekcha", 'callback_data': 'lang_uz'},
    {'text': '🇷🇺 Русский', 'callback_data': 'lang_ru'},
]]}


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    """POST /api/telegram/webhook/<secret>/"""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api = TelegramBotAPI()

    def post(self, request, secret):
        expected = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if not expected or secret != expected:
            return HttpResponse(status=403)

        try:
            update = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return HttpResponse(status=400)

        if 'message' in update:
            self._dispatch_async(self._handle_message, update['message'])
        elif 'callback_query' in update:
            self._dispatch_async(self._handle_callback, update['callback_query'])

        return HttpResponse('ok')

    def _dispatch_async(self, handler, payload):
        """Run *handler* in a daemon thread and let post() return 200 now.

        Telegram waits for the webhook's 200 and **redelivers the same
        update** if it doesn't arrive quickly. With only 3 sync gunicorn
        workers, a /status handler that blocks on systemctl for seconds
        ties up a worker and triggers Telegram's retry storm — the 1-2 min
        "stuck" feeling. Handing the work to a thread frees the worker in
        milliseconds. Each thread owns its DB connections, so close them on
        exit or we leak one per update.
        """
        def _runner():
            try:
                handler(payload)
            except Exception as exc:  # noqa: BLE001
                logger.error('Async webhook handler failed: %s', exc, exc_info=True)
            finally:
                connections.close_all()

        threading.Thread(target=_runner, daemon=True).start()

    # ── Message routing ──────────────────────────────────────────────────────

    def _handle_message(self, message):
        try:
            self._route_message(message)
        except Exception as exc:
            logger.error('Unhandled webhook error: %s', exc, exc_info=True)

    def _route_message(self, message):
        text = message.get('text', '')
        chat = message.get('chat', {})
        chat_type = chat.get('type', '')

        # Emoji input handler — captures text/sticker during pending edit state
        if chat_type == 'private' and handle_emoji_input(message, self.api):
            return

        # Owner pasted a bare IP → offer to add it to the admin allowlist
        if chat_type == 'private' and not text.startswith('/'):
            from servermonitor.handlers import is_owner
            from servermonitor.ip_handlers import maybe_offer_ip_add
            if is_owner(message.get('from', {}).get('id', 0)) \
                    and maybe_offer_ip_add(message, self.api):
                return

        if not text.startswith('/'):
            return
        command = text.split()[0].split('@')[0]  # strip @botname

        if chat_type == 'private':
            self._private_command(command, message)
        elif chat_type in ('group', 'supergroup'):
            self._group_command(command, message)

    # ── Private chat ─────────────────────────────────────────────────────────

    def _owner_start_menu(self, lang: str) -> str:
        """Owner /start menu built from the shared cmd.* catalogue."""
        lines = [t('start.hello', lang, greeting=ce('greeting', '👋')), '']
        for section_key, commands in _START_MENU:
            lines.append(f'{ce("server", "🖥")} <b>{t(section_key, lang)}</b>')
            for cmd, (emoji_key, fallback) in commands:
                icon = ce(emoji_key, fallback) if emoji_key else fallback
                lines.append(f'/{cmd} — {icon} {t(f"cmd.{cmd}", lang)}')
            lines.append('')
        lines.append(f'{ce("clock", "⏰")} <b>{t("start.sec_auto", lang)}</b>')
        lines.append(f'{ce("chart", "📊")} {t("start.auto_daily", lang)}')
        lines.append(f'{ce("alert", "🚨")} {t("start.auto_alerts", lang)}')
        lines.append(f'{ce("scam_warn", "ℹ️")} {t("start.ip_hint", lang)}')
        return '\n'.join(lines)

    def _private_command(self, command, message):
        tg_from = message.get('from', {})
        tg_id = tg_from['id']
        lang = resolve_lang(tg_from)

        # Language chooser — available to everyone
        if command == '/lang':
            self.api.send_message(tg_id, t('lang.choose', lang), reply_markup=_LANG_BUTTONS)
            return

        # Server monitor commands (owner-only)
        if handle_server_command(command, message, self.api):
            return

        if command == '/start':
            from servermonitor.handlers import is_owner
            from servermonitor.ip_handlers import handle_start_payload

            # Deep link: t.me/<bot>?start=addip_<token> (from /myip/ page)
            parts = message.get('text', '').split(maxsplit=1)
            payload = parts[1].strip() if len(parts) > 1 else ''
            if payload and is_owner(tg_id) and handle_start_payload(payload, tg_from, self.api):
                return

            if is_owner(tg_id):
                self.api.send_chat_action(tg_id, 'typing')
                self.api.send_message(tg_id, self._owner_start_menu(lang))
            else:
                self.api.send_message(tg_id, t('start.user_greeting', lang))
        elif command == '/notifications':
            self._show_user_settings(tg_id, lang)

    def _show_user_settings(self, telegram_id: int, lang: str = 'uz'):
        try:
            profile = TelegramEntity.objects.get(telegram_id=telegram_id)
        except TelegramEntity.DoesNotExist:
            self.api.send_message(telegram_id, t('notif.not_logged_in', lang))
            return

        pref, _ = NotificationPreference.objects.get_or_create(profile=profile)
        keyboard = self._build_user_keyboard(pref, lang)
        self.api.send_message(
            telegram_id,
            t('notif.header', lang, icon=ce('notifications_icon', '🔔')),
            reply_markup=keyboard,
        )

    @staticmethod
    def _build_user_keyboard(pref, lang: str = 'uz'):
        r = '✅' if pref.replies_enabled else '❌'
        x = '✅' if pref.reactions_enabled else '❌'
        return {
            'inline_keyboard': [
                [{'text': f'{r} {t("notif.replies", lang)}', 'callback_data': 'toggle_replies'}],
                [{'text': f'{x} {t("notif.reactions", lang)}', 'callback_data': 'toggle_reactions'}],
            ],
        }

    # ── Group commands ───────────────────────────────────────────────────────

    def _group_command(self, command, message):
        site = SiteSettingsService.get()
        chat_id = message['chat']['id']

        # Only respond in the configured admin group
        if site.telegram_admin_group_id and chat_id != site.telegram_admin_group_id:
            return

        if command == '/ban':
            self._handle_ban(message, permanent=True)
        elif command == '/mute':
            self._handle_ban(message, permanent=False)
        elif command == '/config':
            self._show_group_config(chat_id, resolve_lang(message.get('from', {})))

    def _handle_ban(self, message, *, permanent: bool):
        chat_id = message['chat']['id']
        lang = resolve_lang(message.get('from', {}))
        reply_to = message.get('reply_to_message')

        if not reply_to:
            self.api.send_message(
                chat_id, t('group.ban_usage', lang, icon=ce('scam_warn', 'ℹ️')),
            )
            return

        reply_msg_id = reply_to.get('message_id')
        if not reply_msg_id:
            return

        # Look up the user from the admin log
        try:
            log_entry = AdminLogMessage.objects.select_related('profile').get(
                message_id=reply_msg_id,
            )
        except AdminLogMessage.DoesNotExist:
            self.api.send_message(
                chat_id, t('group.user_not_identified', lang, icon=ce('scam_warn', '⚠️')),
            )
            return

        if not log_entry.profile:
            self.api.send_message(
                chat_id, t('group.no_profile', lang, icon=ce('scam_warn', '⚠️')),
            )
            return

        profile = log_entry.profile
        # The banned user gets the DM in THEIR language, not the admin's.
        user_lang = resolve_lang(chat_id=profile.telegram_id)
        # Parse optional reason after the command
        parts = message.get('text', '').split(maxsplit=1)
        reason = parts[1] if len(parts) > 1 else ''

        # Deactivate any existing bans
        UserBan.objects.filter(profile=profile, is_active=True).update(is_active=False)

        if permanent:
            UserBan.objects.create(
                profile=profile,
                ban_type=UserBan.BAN,
                reason=reason,
                is_active=True,
            )
            self.api.send_message(
                chat_id,
                t('group.banned', lang, icon=ce('ban', '🚫'), name=profile.display_name),
            )
            self.api.send_message(
                profile.telegram_id,
                t('group.ban_dm', user_lang, icon=ce('ban', '🚫')),
            )
        else:
            expires = timezone.now() + timedelta(days=MUTE_DAYS)
            UserBan.objects.create(
                profile=profile,
                ban_type=UserBan.MUTE,
                reason=reason,
                expires_at=expires,
                is_active=True,
            )
            until = timezone.localtime(expires).strftime('%Y-%m-%d %H:%M')
            self.api.send_message(
                chat_id,
                t('group.muted', lang, icon=ce('mute', '🔇'),
                  name=profile.display_name, days=MUTE_DAYS, until=until),
            )
            self.api.send_message(
                profile.telegram_id,
                t('group.mute_dm', user_lang, icon=ce('mute', '🔇'),
                  days=MUTE_DAYS, until=until),
            )

    @staticmethod
    def _build_config_keyboard(lang: str = 'uz') -> dict:
        """Build the admin config inline keyboard from current SiteSettings."""
        site = SiteSettingsService.get()

        def _s(val):
            return '✅' if val else '❌'

        rows = []
        for cb_data, field in CONFIG_FIELDS.items():
            rows.append([{
                'text': f'{_s(getattr(site, field, True))} {t(cb_data.replace("cfg_", "cfg."), lang)}',
                'callback_data': cb_data,
            }])
        return {'inline_keyboard': rows}

    def _show_group_config(self, chat_id: int, lang: str = 'uz') -> Optional[int]:
        """Send config keyboard, return message_id."""
        keyboard = self._build_config_keyboard(lang)
        result = self.api.send_message(
            chat_id,
            t('cfg.header', lang, icon=ce('config_icon', '⚙️')),
            reply_markup=keyboard,
        )
        if result and result.get('ok'):
            return result['result']['message_id']
        return None

    # ── Callback queries ─────────────────────────────────────────────────────

    def _handle_callback(self, callback_query):
        data = callback_query.get('data', '')
        # Server monitor callbacks (service restart, refresh, panel)
        if handle_server_callback(data, callback_query, self.api):
            return
        # Admin IP allowlist callbacks (owner check inside)
        from servermonitor.ip_handlers import handle_ip_callback
        if handle_ip_callback(data, callback_query, self.api):
            return
        if data in ('lang_uz', 'lang_ru'):
            self._set_language(callback_query)
        elif data.startswith('toggle_'):
            self._toggle_user_pref(callback_query)
        elif data.startswith('cfg_'):
            self._toggle_admin_setting(callback_query)

    def _set_language(self, cq):
        """lang_uz / lang_ru — persist the chooser tap (open to everyone)."""
        new_lang = cq['data'].replace('lang_', '')
        tg_id = cq['from']['id']
        set_lang(tg_id, new_lang)
        self.api.answer_callback_query(cq['id'], t('cb.updated', new_lang))
        self.api.send_message(tg_id, t('lang.saved', new_lang))

    def _toggle_user_pref(self, cq):
        data = cq['data']
        tg_from = cq.get('from', {})
        tg_id = tg_from['id']
        cb_id = cq['id']
        msg = cq.get('message')
        lang = resolve_lang(tg_from)

        try:
            profile = TelegramEntity.objects.get(telegram_id=tg_id)
            pref, _ = NotificationPreference.objects.get_or_create(profile=profile)
        except TelegramEntity.DoesNotExist:
            self.api.answer_callback_query(cb_id, t('cb.profile_not_found', lang))
            return

        if data == 'toggle_replies':
            pref.replies_enabled = not pref.replies_enabled
        elif data == 'toggle_reactions':
            pref.reactions_enabled = not pref.reactions_enabled
        pref.save()

        # Update keyboard in-place
        if msg and msg.get('message_id'):
            keyboard = self._build_user_keyboard(pref, lang)
            self.api.edit_message_reply_markup(
                chat_id=tg_id,
                message_id=msg['message_id'],
                reply_markup=keyboard,
            )
        self.api.answer_callback_query(cb_id, t('cb.updated', lang))

    def _toggle_admin_setting(self, cq):
        data = cq['data']
        cb_id = cq['id']
        msg = cq.get('message')
        lang = resolve_lang(cq.get('from', {}))

        # Owner-only: config toggles change site-wide SiteSettings.
        from servermonitor.handlers import is_owner
        if not is_owner(cq['from']['id']):
            self.api.answer_callback_query(cb_id, t('cb.no_permission', lang))
            return

        field_name = CONFIG_FIELDS.get(data)
        if not field_name:
            return

        from core.models import SiteSettings
        site = SiteSettings.objects.first()
        if not site:
            self.api.answer_callback_query(cb_id, t('cb.settings_not_found', lang))
            return

        current = getattr(site, field_name)
        setattr(site, field_name, not current)
        site.save(update_fields=[field_name])
        # post_save signal invalidates SiteSettingsService cache

        # Edit the existing message keyboard instead of sending a new one
        if msg and msg.get('message_id') and msg.get('chat', {}).get('id'):
            keyboard = self._build_config_keyboard(lang)
            self.api.edit_message_reply_markup(
                chat_id=msg['chat']['id'],
                message_id=msg['message_id'],
                reply_markup=keyboard,
            )
        self.api.answer_callback_query(cb_id, t('cb.updated', lang))
