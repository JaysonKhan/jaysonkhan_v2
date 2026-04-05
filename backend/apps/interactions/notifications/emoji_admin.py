"""
/emoji admin command — manage custom emoji IDs via Telegram bot.

Owner-only. Supports:
- View all emoji fields with current values
- Edit via inline buttons (send numeric ID, premium sticker, or custom emoji)
- Add dynamic extras (stored in tg_emoji_extra JSONField)
- Clear/delete emoji IDs
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from core.services import SiteSettingsService
from .telegram_api import TelegramBotAPI

logger = logging.getLogger('interactions.notifications')

# ── Emoji Registry ───────────────────────────────────────────────────────────
# key → (db_field_name, fallback_unicode, label, category)

EMOJI_REGISTRY = {
    # Channel Buttons
    'read_more':    ('tg_emoji_read_more',    '📖', 'Read More',    'channel'),
    'google_play':  ('tg_emoji_google_play',  '▶️', 'Google Play',  'channel'),
    'app_store':    ('tg_emoji_app_store',     '🍎', 'App Store',    'channel'),
    'web':          ('tg_emoji_web',           '🌐', 'Web',          'channel'),
    'bot':          ('tg_emoji_bot',           '🤖', 'Bot',          'channel'),
    'comment':      ('tg_emoji_comment',       '💬', 'Comment',      'channel'),
    # Server Monitor
    'server':       ('tg_emoji_server',        '🖥', 'Server',       'monitor'),
    'cpu':          ('tg_emoji_cpu',           '🧠', 'CPU',          'monitor'),
    'ram':          ('tg_emoji_ram',           '💾', 'RAM',          'monitor'),
    'disk':         ('tg_emoji_disk',          '💿', 'Disk',         'monitor'),
    'ok':           ('tg_emoji_ok',            '🟢', 'OK',           'monitor'),
    'warn':         ('tg_emoji_warn',          '🟡', 'Warning',      'monitor'),
    'critical':     ('tg_emoji_critical',      '🔴', 'Critical',     'monitor'),
    'chart':        ('tg_emoji_chart',         '📊', 'Chart',        'monitor'),
    'alert':        ('tg_emoji_alert',         '🚨', 'Alert',        'monitor'),
    'money':        ('tg_emoji_money',         '💰', 'Money',        'monitor'),
}

CATEGORIES = {
    'channel': '📢 Channel Buttons',
    'monitor': '🖥 Server Monitor',
}

# ── Pending state (in-memory, owner-only) ────────────────────────────────────
# {tg_id: {'field': key_or_'extra:name', 'msg_id': int, 'ts': float, 'step': str}}
_pending: dict[int, dict] = {}
PENDING_TIMEOUT = 300  # 5 minutes


def _cleanup_pending():
    now = time.time()
    expired = [k for k, v in _pending.items() if now - v['ts'] > PENDING_TIMEOUT]
    for k in expired:
        del _pending[k]


def _is_owner(tg_id: int) -> bool:
    from servermonitor.handlers import is_owner
    return is_owner(tg_id)


# ── /emoji command ───────────────────────────────────────────────────────────

def handle_emoji_command(command: str, message: dict, api: TelegramBotAPI) -> bool:
    """Handle /emoji command. Returns True if handled."""
    if command != '/emoji':
        return False

    tg_id = message['from']['id']
    if not _is_owner(tg_id):
        api.send_message(tg_id, '🔒 Bu komanda faqat admin uchun.')
        return True

    api.send_chat_action(tg_id, 'typing')
    text, keyboard = _build_emoji_list()
    api.send_message(tg_id, text, reply_markup=keyboard)
    return True


def _build_emoji_list() -> tuple[str, dict]:
    """Build formatted emoji list with inline keyboard."""
    site = SiteSettingsService.get()
    lines = ['🎨 <b>Custom Emoji Sozlamalari</b>\n']
    buttons = []

    for cat_key, cat_title in CATEGORIES.items():
        lines.append(f'\n<b>{cat_title}</b>')
        items = [(k, v) for k, v in EMOJI_REGISTRY.items() if v[3] == cat_key]
        for key, (field, fallback, label, _) in items:
            value = getattr(site, field, '') or ''
            display = f'<code>{value}</code>' if value else '<i>bo\'sh</i>'
            lines.append(f'  {fallback} {label}: {display}')
            buttons.append([
                {'text': f'✏️ {fallback} {label}', 'callback_data': f'emj_edit_{key}'},
                {'text': '🗑', 'callback_data': f'emj_clr_{key}'},
            ])

    # Extras from JSONField
    extras = getattr(site, 'tg_emoji_extra', None) or {}
    if extras:
        lines.append(f'\n<b>➕ Extras</b>')
        for name, eid in extras.items():
            display = f'<code>{eid}</code>' if eid else '<i>bo\'sh</i>'
            lines.append(f'  🔹 {name}: {display}')
            buttons.append([
                {'text': f'✏️ {name}', 'callback_data': f'emj_edit_x:{name}'},
                {'text': '🗑', 'callback_data': f'emj_del_x:{name}'},
            ])

    # Bottom row
    buttons.append([
        {'text': '➕ Yangi emoji', 'callback_data': 'emj_add'},
        {'text': '🔄 Yangilash', 'callback_data': 'emj_back'},
    ])

    return '\n'.join(lines), {'inline_keyboard': buttons}


# ── Callback handler ─────────────────────────────────────────────────────────

def handle_emoji_callback(data: str, cq: dict, api: TelegramBotAPI) -> bool:
    """Handle emj_* callback queries. Returns True if handled."""
    if not data.startswith('emj_'):
        return False

    tg_id = cq['from']['id']
    cb_id = cq['id']

    if not _is_owner(tg_id):
        api.answer_callback_query(cb_id, '🔒 Faqat admin uchun')
        return True

    msg = cq.get('message', {})
    chat_id = msg.get('chat', {}).get('id', tg_id)
    msg_id = msg.get('message_id')

    action = data[4:]  # strip 'emj_'

    if action == 'back':
        _refresh_list(chat_id, msg_id, api)
        api.answer_callback_query(cb_id, 'Yangilandi ✓')

    elif action == 'add':
        _pending[tg_id] = {'field': '_new_name', 'msg_id': msg_id, 'ts': time.time(), 'step': 'name'}
        api.send_message(tg_id, '📝 Yangi emoji uchun <b>nom</b> yuboring (masalan: <code>fire</code>):')
        api.answer_callback_query(cb_id)

    elif action.startswith('edit_x:'):
        extra_name = action[7:]
        _pending[tg_id] = {'field': f'extra:{extra_name}', 'msg_id': msg_id, 'ts': time.time(), 'step': 'id'}
        api.send_message(tg_id, (
            f'✏️ <b>{extra_name}</b> uchun yangi emoji ID yuboring:\n\n'
            '💡 Raqam, premium stiker, yoki custom emoji yuborishingiz mumkin.'
        ))
        api.answer_callback_query(cb_id)

    elif action.startswith('edit_'):
        key = action[5:]
        if key not in EMOJI_REGISTRY:
            api.answer_callback_query(cb_id, '⚠️ Noma\'lum emoji')
            return True
        _, fallback, label, _ = EMOJI_REGISTRY[key]
        _pending[tg_id] = {'field': key, 'msg_id': msg_id, 'ts': time.time(), 'step': 'id'}
        api.send_message(tg_id, (
            f'✏️ <b>{fallback} {label}</b> uchun yangi emoji ID yuboring:\n\n'
            '💡 Raqam, premium stiker, yoki custom emoji yuborishingiz mumkin.\n'
            'Bekor qilish: /cancel'
        ))
        api.answer_callback_query(cb_id)

    elif action.startswith('clr_'):
        key = action[4:]
        if key in EMOJI_REGISTRY:
            _save_emoji(key, '')
            api.answer_callback_query(cb_id, '🗑 Tozalandi')
            _refresh_list(chat_id, msg_id, api)
        else:
            api.answer_callback_query(cb_id, '⚠️ Noma\'lum')

    elif action.startswith('del_x:'):
        extra_name = action[6:]
        _delete_extra(extra_name)
        api.answer_callback_query(cb_id, f'🗑 {extra_name} o\'chirildi')
        _refresh_list(chat_id, msg_id, api)

    else:
        api.answer_callback_query(cb_id)

    return True


# ── Input handler (text/sticker during pending state) ────────────────────────

def handle_emoji_input(message: dict, api: TelegramBotAPI) -> bool:
    """
    Handle text/sticker input when emoji edit is pending.
    Returns True if message was consumed, False to pass through.
    """
    _cleanup_pending()
    tg_id = message.get('from', {}).get('id')
    if not tg_id or tg_id not in _pending:
        return False
    if not _is_owner(tg_id):
        return False

    state = _pending[tg_id]
    text = message.get('text', '').strip()

    # Cancel
    if text == '/cancel':
        del _pending[tg_id]
        api.send_message(tg_id, '❌ Bekor qilindi.')
        return True

    # Step: waiting for name (new extra emoji)
    if state['step'] == 'name':
        if not text or not text.replace('_', '').isalnum():
            api.send_message(tg_id, '⚠️ Nom faqat harf, raqam va _ bo\'lishi kerak. Qayta yuboring:')
            return True
        state['field'] = f'extra:{text}'
        state['step'] = 'id'
        state['ts'] = time.time()
        api.send_message(tg_id, (
            f'✅ Nom: <b>{text}</b>\n\n'
            '📝 Endi emoji ID yuboring (raqam, premium stiker, yoki custom emoji):'
        ))
        return True

    # Step: waiting for emoji ID
    if state['step'] == 'id':
        emoji_id = _extract_emoji_id(message)
        if not emoji_id:
            api.send_message(tg_id, (
                '⚠️ Emoji ID topilmadi.\n\n'
                '💡 Premium stiker yuboring, yoki raqam (masalan: <code>5310157785063778846</code>)\n'
                'Bekor qilish: /cancel'
            ))
            return True

        field = state['field']
        msg_id = state.get('msg_id')
        del _pending[tg_id]

        # Save
        if field.startswith('extra:'):
            extra_name = field[6:]
            _save_extra(extra_name, emoji_id)
            label = extra_name
        else:
            _save_emoji(field, emoji_id)
            _, fallback, label, _ = EMOJI_REGISTRY.get(field, ('', '', field, ''))

        api.send_message(tg_id, f'✅ <b>{label}</b> saqlandi: <code>{emoji_id}</code>')

        # Refresh list if we have the message ID
        if msg_id:
            _refresh_list(tg_id, msg_id, api)

        return True

    return False


# ── Emoji ID extraction ──────────────────────────────────────────────────────

def _extract_emoji_id(message: dict) -> str:
    """Extract custom emoji ID from message (sticker, entity, or plain number)."""
    # 1. Premium sticker with custom_emoji_id
    sticker = message.get('sticker')
    if sticker:
        eid = sticker.get('custom_emoji_id')
        if eid:
            return str(eid)

    # 2. Custom emoji entity in message text
    entities = message.get('entities', [])
    for ent in entities:
        if ent.get('type') == 'custom_emoji':
            eid = ent.get('custom_emoji_id')
            if eid:
                return str(eid)

    # 3. Plain numeric ID
    text = message.get('text', '').strip()
    if text.isdigit() and len(text) > 10:
        return text

    return ''


# ── Save helpers ─────────────────────────────────────────────────────────────

def _save_emoji(key: str, value: str) -> None:
    """Save emoji ID to a SiteSettings model field."""
    if key not in EMOJI_REGISTRY:
        return
    field_name = EMOJI_REGISTRY[key][0]
    from core.models import SiteSettings
    site = SiteSettings.objects.first()
    if not site:
        return
    setattr(site, field_name, value)
    site.save(update_fields=[field_name])
    # Reset formatter cache
    try:
        from servermonitor.formatters import reset_emoji_cache
        reset_emoji_cache()
    except Exception:
        pass


def _save_extra(name: str, value: str) -> None:
    """Save emoji ID to tg_emoji_extra JSONField."""
    from core.models import SiteSettings
    site = SiteSettings.objects.first()
    if not site:
        return
    extras = site.tg_emoji_extra or {}
    extras[name] = value
    site.tg_emoji_extra = extras
    site.save(update_fields=['tg_emoji_extra'])
    try:
        from servermonitor.formatters import reset_emoji_cache
        reset_emoji_cache()
    except Exception:
        pass


def _delete_extra(name: str) -> None:
    """Delete an emoji from tg_emoji_extra JSONField."""
    from core.models import SiteSettings
    site = SiteSettings.objects.first()
    if not site:
        return
    extras = site.tg_emoji_extra or {}
    extras.pop(name, None)
    site.tg_emoji_extra = extras
    site.save(update_fields=['tg_emoji_extra'])
    try:
        from servermonitor.formatters import reset_emoji_cache
        reset_emoji_cache()
    except Exception:
        pass


def _refresh_list(chat_id: int, msg_id: int, api: TelegramBotAPI) -> None:
    """Refresh the emoji list message in-place."""
    text, keyboard = _build_emoji_list()
    api.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text=text,
        reply_markup=keyboard,
    )
