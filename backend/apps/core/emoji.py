"""
Centralized custom emoji helper.

Usage:
    from core.emoji import ce
    text = f'{ce("chart", "📊")} Server Health Report'

Returns <tg-emoji emoji-id="ID">fallback</tg-emoji> if custom ID is set,
otherwise returns the plain Unicode fallback.
"""
from __future__ import annotations

import logging

logger = logging.getLogger('core.emoji')

# All tg_emoji_* field names that exist on SiteSettings
_ALL_FIELDS = [
    # Channel
    'read_more', 'google_play', 'app_store', 'web', 'bot', 'comment',
    # Monitor
    'server', 'cpu', 'ram', 'disk', 'ok', 'warn', 'critical', 'chart', 'alert', 'money',
    # Notification
    'reply', 'like', 'contact_msg',
    # Admin Log
    'user', 'returning', 'premium', 'osint', 'education',
    # Command
    'greeting', 'ban', 'mute', 'lock',
    # Channel Sharing
    'post', 'project', 'tech',
]

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    try:
        from core.services import SiteSettingsService
        site = SiteSettingsService.get()
        _cache = {}
        for key in _ALL_FIELDS:
            field = f'tg_emoji_{key}'
            _cache[key] = getattr(site, field, '') or ''
        # Merge extras
        extras = getattr(site, 'tg_emoji_extra', None) or {}
        if isinstance(extras, dict):
            for k, v in extras.items():
                if v and isinstance(v, str):
                    _cache[k] = v
    except Exception:
        logger.error('Failed to load emoji cache', exc_info=True)
        _cache = {}
    return _cache


def reset_cache():
    """Reset emoji cache. Call after SiteSettings save."""
    global _cache
    _cache = None


def ce(key: str, fallback: str) -> str:
    """Custom Emoji — returns <tg-emoji> tag if ID set, else Unicode fallback."""
    emojis = _load()
    eid = emojis.get(key, '')
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'
    return fallback
