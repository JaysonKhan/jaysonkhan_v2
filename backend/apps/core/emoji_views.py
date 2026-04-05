"""
Emoji Manager — standalone admin page for managing custom emoji IDs.

Professional CRUD interface for all tg_emoji_* fields + dynamic extras.
Accessible at ADMIN_URL/emoji/.
"""
from __future__ import annotations

import re

from django.contrib import admin, messages
from django.template.response import TemplateResponse

from core.decorators import admin_permission_required
from core.models import SiteSettings

_VALID_NAME = re.compile(r'^[a-zA-Z0-9_]+$')
_VALID_ID = re.compile(r'^\d*$')  # empty or numeric

# Same registry as bot emoji_admin.py
EMOJI_FIELDS = [
    # (key, db_field, fallback, label, category)
    ('read_more',   'tg_emoji_read_more',   '📖', 'Read More',   'channel'),
    ('google_play', 'tg_emoji_google_play', '▶️', 'Google Play', 'channel'),
    ('app_store',   'tg_emoji_app_store',   '🍎', 'App Store',   'channel'),
    ('web',         'tg_emoji_web',         '🌐', 'Web',         'channel'),
    ('bot',         'tg_emoji_bot',         '🤖', 'Bot',         'channel'),
    ('comment',     'tg_emoji_comment',     '💬', 'Comment',     'channel'),
    ('server',      'tg_emoji_server',      '🖥', 'Server',      'monitor'),
    ('cpu',         'tg_emoji_cpu',         '🧠', 'CPU',         'monitor'),
    ('ram',         'tg_emoji_ram',         '💾', 'RAM',         'monitor'),
    ('disk',        'tg_emoji_disk',        '💿', 'Disk',        'monitor'),
    ('ok',          'tg_emoji_ok',          '🟢', 'OK',          'monitor'),
    ('warn',        'tg_emoji_warn',        '🟡', 'Warning',     'monitor'),
    ('critical',    'tg_emoji_critical',    '🔴', 'Critical',    'monitor'),
    ('chart',       'tg_emoji_chart',       '📊', 'Chart',       'monitor'),
    ('alert',       'tg_emoji_alert',       '🚨', 'Alert',       'monitor'),
    ('money',       'tg_emoji_money',       '💰', 'Money',       'monitor'),
]

CATEGORIES = [
    ('channel', '📢 Channel Buttons', 'Inline button emojilar (icon_custom_emoji_id)'),
    ('monitor', '🖥 Server Monitor', 'Server health report xabarlaridagi emojilar'),
    ('extra',   '➕ Dynamic Extras', 'Qo\'shimcha custom emojilar (tg_emoji_extra JSON)'),
]


def _ctx(request, extra=None):
    ctx = admin.site.each_context(request)
    ctx.update({
        'title': 'Emoji Manager',
        'subtitle': 'Custom Emoji ID Sozlamalari',
        **(extra or {}),
    })
    return ctx


@admin_permission_required('core.change_sitesettings')
def emoji_manager(request):
    """Main emoji manager page — list all emoji fields with edit forms."""
    site = SiteSettings.load()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'save_fields':
            # Save model fields
            update_fields = []
            for key, field, *_ in EMOJI_FIELDS:
                new_val = request.POST.get(f'field_{key}', '').strip()
                old_val = getattr(site, field, '') or ''
                if new_val != old_val:
                    setattr(site, field, new_val)
                    update_fields.append(field)
            if update_fields:
                site.save(update_fields=update_fields)
                _reset_caches()
                messages.success(request, f'{len(update_fields)} ta emoji yangilandi.')
            else:
                messages.info(request, 'O\'zgarish yo\'q.')

        elif action == 'save_extras':
            # Save extras from form
            extras = {}
            names = request.POST.getlist('extra_name')
            values = request.POST.getlist('extra_value')
            for name, val in zip(names, values):
                name = name.strip()
                val = val.strip()
                if not name:
                    continue
                if not _VALID_NAME.match(name):
                    messages.warning(request, f'Noto\'g\'ri nom: "{name}" — faqat harf, raqam, _')
                    continue
                if val and not _VALID_ID.match(val):
                    messages.warning(request, f'Noto\'g\'ri ID: "{val}" — faqat raqam')
                    continue
                extras[name] = val
            site.tg_emoji_extra = extras
            site.save(update_fields=['tg_emoji_extra'])
            _reset_caches()
            messages.success(request, f'{len(extras)} ta extra emoji saqlandi.')

        elif action == 'add_extra':
            name = request.POST.get('new_name', '').strip()
            value = request.POST.get('new_value', '').strip()
            if not name:
                messages.error(request, 'Nom kiritilmadi.')
            elif not _VALID_NAME.match(name):
                messages.error(request, f'Noto\'g\'ri nom: faqat harf, raqam, _')
            elif value and not _VALID_ID.match(value):
                messages.error(request, f'Noto\'g\'ri ID: faqat raqam')
            else:
                extras = site.tg_emoji_extra or {}
                extras[name] = value
                site.tg_emoji_extra = extras
                site.save(update_fields=['tg_emoji_extra'])
                _reset_caches()
                messages.success(request, f'"{name}" qo\'shildi.')

        elif action == 'delete_extra':
            name = request.POST.get('delete_name', '')
            extras = site.tg_emoji_extra or {}
            if name in extras:
                del extras[name]
                site.tg_emoji_extra = extras
                site.save(update_fields=['tg_emoji_extra'])
                _reset_caches()
                messages.success(request, f'"{name}" o\'chirildi.')

        elif action == 'clear_all':
            update_fields = []
            for key, field, *_ in EMOJI_FIELDS:
                if getattr(site, field, ''):
                    setattr(site, field, '')
                    update_fields.append(field)
            if site.tg_emoji_extra:
                site.tg_emoji_extra = {}
                update_fields.append('tg_emoji_extra')
            if update_fields:
                site.save(update_fields=update_fields)
                _reset_caches()
                messages.warning(request, 'Barcha emojilar tozalandi.')

    # Build context
    categories = []
    for cat_key, cat_title, cat_desc in CATEGORIES:
        if cat_key == 'extra':
            continue
        items = []
        for key, field, fallback, label, cat in EMOJI_FIELDS:
            if cat != cat_key:
                continue
            value = getattr(site, field, '') or ''
            items.append({
                'key': key,
                'field': field,
                'fallback': fallback,
                'label': label,
                'value': value,
            })
        categories.append({
            'key': cat_key,
            'title': cat_title,
            'description': cat_desc,
            'items': items,
        })

    extras = site.tg_emoji_extra or {}
    extra_items = [{'name': k, 'value': v} for k, v in extras.items()]

    filled = sum(1 for _, f, *_ in EMOJI_FIELDS if getattr(site, f, ''))
    total = len(EMOJI_FIELDS) + len(extras)
    filled += sum(1 for v in extras.values() if v)

    return TemplateResponse(request, 'core/emoji_manager.html', _ctx(request, {
        'categories': categories,
        'extra_items': extra_items,
        'stats': {
            'total': total,
            'filled': filled,
            'empty': total - filled,
        },
    }))


def _reset_caches():
    """Reset all emoji-related caches."""
    try:
        from servermonitor.formatters import reset_emoji_cache
        reset_emoji_cache()
    except Exception:
        pass
