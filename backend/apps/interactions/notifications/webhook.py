"""
Telegram Bot webhook receiver.

Handles:
- Private chat: /start, /notifications (inline keyboard toggles)
- Admin group:  /ban, /mute (reply to logged message), /config
- Callback queries for inline keyboard presses
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.services import SiteSettingsService
from interactions.models import (
    NotificationPreference,
    UserBan,
    AdminLogMessage,
)
from servermonitor.handlers import handle_server_callback, handle_server_command
from telegram.models import TelegramEntity
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
            self._handle_message(update['message'])
        elif 'callback_query' in update:
            self._handle_callback(update['callback_query'])

        return HttpResponse('ok')

    # ── Message routing ──────────────────────────────────────────────────────

    def _handle_message(self, message):
        text = message.get('text', '')
        if not text.startswith('/'):
            return

        chat = message.get('chat', {})
        chat_type = chat.get('type', '')
        command = text.split()[0].split('@')[0]  # strip @botname

        if chat_type == 'private':
            self._private_command(command, message)
        elif chat_type in ('group', 'supergroup'):
            self._group_command(command, message)

    # ── Private chat ─────────────────────────────────────────────────────────

    def _private_command(self, command, message):
        tg_id = message['from']['id']

        # Server monitor commands (owner-only)
        if handle_server_command(command, message, self.api):
            return

        if command == '/start':
            from servermonitor.handlers import is_owner
            if is_owner(tg_id):
                self.api.send_message(tg_id, (
                    '👋 <b>Salom, Admin!</b>\n\n'
                    '🔧 <b>Server Monitor</b>\n'
                    '┌─────────────────────────\n'
                    '│ /status  — 📊 Server holati (CPU, RAM, disk)\n'
                    '│ /services — 🔧 Systemd servislar holati\n'
                    '│ /disk — 💿 Disk ishlatilishi (batafsil)\n'
                    '│ /tariff — 💰 Contabo tarif tavsiyasi\n'
                    '│ /logs — 📋 Servis loglari (/logs nginx 30)\n'
                    '│ /backup — 💾 PostgreSQL backup yaratish\n'
                    '└─────────────────────────\n\n'
                    '🔔 <b>Bildirishnomalar</b>\n'
                    '┌─────────────────────────\n'
                    '│ /notifications — sozlamalar\n'
                    '│ /config — admin guruh sozlamalari\n'
                    '└─────────────────────────\n\n'
                    '⏰ <b>Avtomatik</b>\n'
                    '┌─────────────────────────\n'
                    '│ 📊 Kunlik hisobot — har kuni 09:00\n'
                    '│ 🚨 CPU alert — har 10 daqiqada (>75%)\n'
                    '└─────────────────────────'
                ))
            else:
                self.api.send_message(tg_id, (
                    'Salom! Men sizga kommentlaringizga javob kelganda '
                    'yoki reaksiya qo\'yilganda xabar beraman.\n\n'
                    'Sozlamalar: /notifications'
                ))
        elif command == '/notifications':
            self._show_user_settings(tg_id)

    def _show_user_settings(self, telegram_id: int):
        try:
            profile = TelegramEntity.objects.get(telegram_id=telegram_id)
        except TelegramEntity.DoesNotExist:
            self.api.send_message(telegram_id, (
                'Siz hali saytga kirmagansiz. Avval jaysonkhan.com da '
                'Telegram orqali login qiling.'
            ))
            return

        pref, _ = NotificationPreference.objects.get_or_create(profile=profile)
        keyboard = self._build_user_keyboard(pref)
        self.api.send_message(
            telegram_id,
            '🔔 <b>Bildirishnoma sozlamalari</b>',
            reply_markup=keyboard,
        )

    @staticmethod
    def _build_user_keyboard(pref):
        r = '✅' if pref.replies_enabled else '❌'
        x = '✅' if pref.reactions_enabled else '❌'
        return {
            'inline_keyboard': [
                [{'text': f'{r} Javoblar (replies)', 'callback_data': 'toggle_replies'}],
                [{'text': f'{x} Reaksiyalar', 'callback_data': 'toggle_reactions'}],
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
            self._show_group_config(chat_id)

    def _handle_ban(self, message, *, permanent: bool):
        chat_id = message['chat']['id']
        reply_to = message.get('reply_to_message')

        if not reply_to:
            self.api.send_message(
                chat_id, 'ℹ️ Foydalanuvchi xabariga reply qilib /ban yoki /mute yuboring.',
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
            self.api.send_message(chat_id, '⚠️ Bu xabardan foydalanuvchini aniqlab bo\'lmadi.')
            return

        if not log_entry.profile:
            self.api.send_message(chat_id, '⚠️ Bu eventda foydalanuvchi profili yo\'q.')
            return

        profile = log_entry.profile
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
            self.api.send_message(chat_id, f'🚫 <b>{profile.display_name}</b> doimiy ban qilindi.')
            self.api.send_message(
                profile.telegram_id,
                '🚫 Siz jaysonkhan.com da komment yozishdan doimiy bloklangansiz.',
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
                f'🔇 <b>{profile.display_name}</b> {MUTE_DAYS} kunga mute qilindi ({until} gacha).',
            )
            self.api.send_message(
                profile.telegram_id,
                f'🔇 Siz jaysonkhan.com da {MUTE_DAYS} kunga mute qilindingiz ({until} gacha).',
            )

    @staticmethod
    def _build_config_keyboard() -> dict:
        """Build the admin config inline keyboard from current SiteSettings."""
        site = SiteSettingsService.get()

        def _s(val):
            return '✅' if val else '❌'

        labels = {
            'cfg_new_users': 'Yangi userlar',
            'cfg_comments': 'Kommentlar',
            'cfg_replies': 'Javoblar',
            'cfg_reactions': 'Reaksiyalar',
            'cfg_likes': 'Likelar',
            'cfg_contacts': 'Contact xabarlar',
        }
        rows = []
        for cb_data, label in labels.items():
            field = CONFIG_FIELDS[cb_data]
            rows.append([{
                'text': f'{_s(getattr(site, field, True))} {label}',
                'callback_data': cb_data,
            }])
        return {'inline_keyboard': rows}

    def _show_group_config(self, chat_id: int) -> Optional[int]:
        """Send config keyboard, return message_id."""
        keyboard = self._build_config_keyboard()
        result = self.api.send_message(
            chat_id, '⚙️ <b>Admin guruh sozlamalari</b>', reply_markup=keyboard,
        )
        if result and result.get('ok'):
            return result['result']['message_id']
        return None

    # ── Callback queries ─────────────────────────────────────────────────────

    def _handle_callback(self, callback_query):
        data = callback_query.get('data', '')
        # Server monitor callbacks (service restart, refresh)
        if handle_server_callback(data, callback_query, self.api):
            return
        if data.startswith('toggle_'):
            self._toggle_user_pref(callback_query)
        elif data.startswith('cfg_'):
            self._toggle_admin_setting(callback_query)

    def _toggle_user_pref(self, cq):
        data = cq['data']
        tg_id = cq['from']['id']
        cb_id = cq['id']
        msg = cq.get('message')

        try:
            profile = TelegramEntity.objects.get(telegram_id=tg_id)
            pref, _ = NotificationPreference.objects.get_or_create(profile=profile)
        except TelegramEntity.DoesNotExist:
            self.api.answer_callback_query(cb_id, 'Profil topilmadi')
            return

        if data == 'toggle_replies':
            pref.replies_enabled = not pref.replies_enabled
        elif data == 'toggle_reactions':
            pref.reactions_enabled = not pref.reactions_enabled
        pref.save()

        # Update keyboard in-place
        if msg and msg.get('message_id'):
            keyboard = self._build_user_keyboard(pref)
            self.api.edit_message_reply_markup(
                chat_id=tg_id,
                message_id=msg['message_id'],
                reply_markup=keyboard,
            )
        self.api.answer_callback_query(cb_id, 'Yangilandi ✓')

    def _toggle_admin_setting(self, cq):
        data = cq['data']
        cb_id = cq['id']
        msg = cq.get('message')

        field_name = CONFIG_FIELDS.get(data)
        if not field_name:
            return

        from core.models import SiteSettings
        site = SiteSettings.objects.first()
        if not site:
            self.api.answer_callback_query(cb_id, 'SiteSettings topilmadi')
            return

        current = getattr(site, field_name)
        setattr(site, field_name, not current)
        site.save(update_fields=[field_name])
        # post_save signal invalidates SiteSettingsService cache

        # Edit the existing message keyboard instead of sending a new one
        if msg and msg.get('message_id') and msg.get('chat', {}).get('id'):
            keyboard = self._build_config_keyboard()
            self.api.edit_message_reply_markup(
                chat_id=msg['chat']['id'],
                message_id=msg['message_id'],
                reply_markup=keyboard,
            )
        self.api.answer_callback_query(cb_id, 'Yangilandi ✓')
