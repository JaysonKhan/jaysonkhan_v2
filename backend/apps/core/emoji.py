"""
Centralized custom emoji helper.

Usage:
    from core.emoji import ce
    text = f'{ce("chart", "📊")} Server Health Report'
"""
from __future__ import annotations

import logging

logger = logging.getLogger('core.emoji')

_ALL_FIELDS = [
    # Channel (9)
    'read_more', 'google_play', 'app_store', 'web', 'bot', 'comment', 'post', 'project', 'tech',
    # Monitor (22)
    'server', 'cpu', 'ram', 'disk', 'ok', 'warn', 'critical', 'chart', 'alert', 'money',
    'clock', 'uptime', 'load', 'swap', 'services_icon', 'trophy', 'nginx', 'postgresql',
    'package', 'upgrade', 'downgrade',
    # Notification (4)
    'reply', 'like', 'unlike', 'contact_msg',
    # Admin Log (16)
    'user', 'returning', 'premium', 'osint', 'education',
    'group', 'channel_icon', 'id_badge', 'phone', 'sources', 'crown',
    'verified', 'scam_warn', 'history', 'pencil', 'calendar',
    # Command (10)
    'greeting', 'ban', 'mute', 'lock',
    'notifications_icon', 'config_icon', 'error', 'success', 'backup_icon', 'logs_icon',
    # Bot Status (4)
    'warning', 'red_dot', 'green_dot', 'blocked',
    # Bot Actions (4)
    'plus', 'minus', 'edit', 'right_arrow',
    # Bot Navigation (4)
    'point_right', 'point_down', 'back', 'home',
    # Bot Awards (3)
    'gold', 'silver', 'bronze',
    # Bot People (5)
    'person', 'people', 'teacher', 'crown_icon', 'eye',
    # Bot Communication (6)
    'mail', 'upload', 'email_icon', 'phone_icon', 'thought', 'speech',
    # Bot Data (7)
    'stats', 'growth', 'document', 'name_badge', 'mobile', 'device', 'numbers',
    # Bot System (6)
    'settings', 'secure', 'locked', 'key', 'shield', 'cloud',
    # Bot Misc (19)
    'globe', 'moon', 'clover', 'target', 'diamond', 'control',
    'fire', 'triangle', 'graduation', 'pray', 'school', 'ballot',
    'blue_square', 'lightning', 'celebration', 'memo', 'pin', 'undo', 'skip',
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
    global _cache
    _cache = None


def ce(key: str, fallback: str) -> str:
    emojis = _load()
    eid = emojis.get(key, '')
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'
    return fallback
