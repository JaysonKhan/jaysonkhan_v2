"""
Per-chat bot language resolution.

Priority: explicit /lang preference (BotChatPref row) → the Telegram
client's language_code → 'uz'. All lookups fail open to 'uz' so a DB
hiccup can never break a handler.
"""
from __future__ import annotations

from core.bot_i18n import DEFAULT_LANG, LANGS


def resolve_lang(tg_from: dict | None = None, chat_id: int | None = None) -> str:
    """Language for replies to this user/chat.

    *tg_from* is Telegram's `from` dict (has `id` + optional `language_code`);
    pass *chat_id* alone when no user dict is at hand (cron → owner).
    """
    cid = chat_id or (tg_from or {}).get('id')
    if cid:
        try:
            from interactions.models import BotChatPref
            pref = BotChatPref.objects.filter(chat_id=cid).values_list('language', flat=True).first()
            if pref in LANGS:
                return pref
        except Exception:  # noqa: BLE001 — DB issues must not break replies
            pass
    code = ((tg_from or {}).get('language_code') or '').lower()
    if code.startswith('ru'):
        return 'ru'
    return DEFAULT_LANG


def set_lang(chat_id: int, lang: str) -> bool:
    """Persist an explicit language choice. Returns success."""
    if lang not in LANGS or not chat_id:
        return False
    try:
        from interactions.models import BotChatPref
        BotChatPref.objects.update_or_create(
            chat_id=chat_id, defaults={'language': lang},
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def owner_lang() -> str:
    """Language for owner-directed cron alerts/reports."""
    try:
        from core.services import SiteSettingsService
        owner_id = SiteSettingsService.get().telegram_owner_id
        if owner_id:
            return resolve_lang(chat_id=owner_id)
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_LANG
