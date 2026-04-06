"""
Auto emoji ID extractor for owner.

When the site owner sends a message containing custom emoji or
a premium sticker in private chat, the bot automatically replies
with the emoji ID(s). No command needed — always active.
"""
from __future__ import annotations

from .telegram_api import TelegramBotAPI


def _is_owner(tg_id: int) -> bool:
    from servermonitor.handlers import is_owner
    return is_owner(tg_id)


def handle_emoji_input(message: dict, api: TelegramBotAPI) -> bool:
    """
    Auto-extract custom emoji IDs from owner messages.
    Returns True if emoji was found and response sent.
    """
    tg_id = message.get('from', {}).get('id')
    if not tg_id or not _is_owner(tg_id):
        return False

    # Skip command messages
    text = message.get('text', '').strip()
    if text.startswith('/'):
        return False

    # 1. Premium sticker with custom_emoji_id
    sticker = message.get('sticker')
    if sticker:
        eid = sticker.get('custom_emoji_id')
        if eid:
            api.send_message(tg_id, f'<code>{eid}</code>')
            return True
        return False  # Regular sticker — ignore silently

    # 2. Custom emoji entities in text
    entities = message.get('entities') or []
    found = []
    for ent in entities:
        if ent.get('type') == 'custom_emoji':
            eid = ent.get('custom_emoji_id')
            if eid:
                found.append(str(eid))

    if found:
        if len(found) == 1:
            api.send_message(tg_id, f'<code>{found[0]}</code>')
        else:
            lines = [f'{i}. <code>{eid}</code>' for i, eid in enumerate(found, 1)]
            api.send_message(tg_id, '\n'.join(lines))
        return True

    return False


def handle_emoji_command(command: str, message: dict, api: TelegramBotAPI) -> bool:
    """No longer used — kept for backward compatibility."""
    return False


def handle_emoji_callback(data: str, cq: dict, api: TelegramBotAPI) -> bool:
    return False
