"""
/emoji bot command — simple emoji ID extractor tool.

Send any custom emoji or premium sticker → bot returns its ID.
Emoji CRUD is done in Django admin panel, not here.
"""
from __future__ import annotations

import logging
import time

from core.services import SiteSettingsService
from .telegram_api import TelegramBotAPI

logger = logging.getLogger('interactions.notifications')

# ── Emoji Registry (for display only) ────────────────────────────────────────

EMOJI_REGISTRY = {
    'read_more':    ('tg_emoji_read_more',    '📖', 'Read More',    'channel'),
    'google_play':  ('tg_emoji_google_play',  '▶️', 'Google Play',  'channel'),
    'app_store':    ('tg_emoji_app_store',     '🍎', 'App Store',    'channel'),
    'web':          ('tg_emoji_web',           '🌐', 'Web',          'channel'),
    'bot':          ('tg_emoji_bot',           '🤖', 'Bot',          'channel'),
    'comment':      ('tg_emoji_comment',       '💬', 'Comment',      'channel'),
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

# ── Pending state for ID extraction mode ─────────────────────────────────────
_pending_extract: dict[int, float] = {}  # {tg_id: timestamp}
PENDING_TIMEOUT = 120  # 2 minutes


def _is_owner(tg_id: int) -> bool:
    from servermonitor.handlers import is_owner
    return is_owner(tg_id)


# ── /emoji command ───────────────────────────────────────────────────────────

def handle_emoji_command(command: str, message: dict, api: TelegramBotAPI) -> bool:
    if command != '/emoji':
        return False

    tg_id = message['from']['id']
    if not _is_owner(tg_id):
        api.send_message(tg_id, '🔒 Bu komanda faqat admin uchun.')
        return True

    api.send_chat_action(tg_id, 'typing')
    site = SiteSettingsService.get()

    lines = ['🎨 <b>Custom Emoji Sozlamalari</b>\n']

    for cat_key, cat_title in CATEGORIES.items():
        lines.append(f'<b>{cat_title}</b>')
        items = [(k, v) for k, v in EMOJI_REGISTRY.items() if v[3] == cat_key]
        for key, (field, fallback, label, _) in items:
            value = getattr(site, field, '') or ''
            if value:
                lines.append(f'  {fallback} {label}: <code>{value}</code>')
            else:
                lines.append(f'  {fallback} {label}: <i>—</i>')
        lines.append('')

    # Extras
    extras = getattr(site, 'tg_emoji_extra', None) or {}
    if extras:
        lines.append('<b>➕ Extras</b>')
        for name, eid in extras.items():
            lines.append(f'  🔹 {name}: <code>{eid}</code>')
        lines.append('')

    lines.append('─────────────────────────')
    lines.append('📝 <b>Emoji ID olish:</b>')
    lines.append('Custom emoji yoki premium stiker yuboring —')
    lines.append('bot ID ni qaytaradi.')
    lines.append('')
    lines.append('⚙️ <b>Sozlash:</b> Admin panel → Emoji Manager')

    # Enter extract mode
    _pending_extract[tg_id] = time.time()

    api.send_message(tg_id, '\n'.join(lines))
    return True


# ── Input handler — extract emoji ID from sticker/emoji ──────────────────────

def handle_emoji_input(message: dict, api: TelegramBotAPI) -> bool:
    """If owner is in extract mode, return emoji ID from sticker/custom emoji."""
    # Cleanup expired
    now = time.time()
    expired = [k for k, v in _pending_extract.items() if now - v > PENDING_TIMEOUT]
    for k in expired:
        del _pending_extract[k]

    tg_id = message.get('from', {}).get('id')
    if not tg_id or tg_id not in _pending_extract:
        return False

    text = message.get('text', '').strip()

    # Commands exit extract mode
    if text.startswith('/'):
        del _pending_extract[tg_id]
        return False

    # Try to extract emoji ID
    sticker = message.get('sticker')
    if sticker:
        eid = sticker.get('custom_emoji_id')
        if eid:
            _pending_extract[tg_id] = time.time()  # keep mode active
            api.send_message(tg_id, (
                f'✅ <b>Custom Emoji ID:</b>\n\n'
                f'<code>{eid}</code>\n\n'
                f'📋 ID nusxalandi. Admin panelda qo\'ying.'
            ))
            return True
        # Regular sticker
        set_name = sticker.get('set_name', '?')
        api.send_message(tg_id, (
            f'⚠️ Bu oddiy stiker (set: <code>{set_name}</code>)\n'
            f'Custom emoji emas — ID yo\'q.\n\n'
            f'💡 Xabarga custom emoji qo\'yib yuboring.'
        ))
        return True

    # Custom emoji entities in text
    entities = message.get('entities', [])
    found_ids = []
    for ent in entities:
        if ent.get('type') == 'custom_emoji':
            eid = ent.get('custom_emoji_id')
            if eid:
                found_ids.append(str(eid))

    if found_ids:
        _pending_extract[tg_id] = time.time()
        if len(found_ids) == 1:
            api.send_message(tg_id, (
                f'✅ <b>Custom Emoji ID:</b>\n\n'
                f'<code>{found_ids[0]}</code>\n\n'
                f'📋 Admin panelda qo\'ying.'
            ))
        else:
            lines = ['✅ <b>Custom Emoji IDlar:</b>\n']
            for i, eid in enumerate(found_ids, 1):
                lines.append(f'{i}. <code>{eid}</code>')
            lines.append(f'\n📋 {len(found_ids)} ta emoji topildi.')
            api.send_message(tg_id, '\n'.join(lines))
        return True

    # Plain text — not consumed, let other handlers process
    return False


# ── Callback handler (no-op now, but keep interface for webhook) ─────────────

def handle_emoji_callback(data: str, cq: dict, api: TelegramBotAPI) -> bool:
    """No emoji callbacks anymore — all managed in admin panel."""
    return False
