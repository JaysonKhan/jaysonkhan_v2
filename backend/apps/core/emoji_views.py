"""
Telegram Settings — custom admin page for managing Telegram bot configuration.

Emoji Manager tab: all tg_emoji_* fields for customizing bot messages.
Accessible at ADMIN_URL/telegram/settings/.
"""
from __future__ import annotations

from django.contrib import admin, messages
from django.template.response import TemplateResponse

from core.decorators import admin_permission_required
from core.models import SiteSettings

# ── Emoji Registry ───────────────────────────────────────────────────────────

EMOJI_FIELDS = [
    ('read_more',   'tg_emoji_read_more',   '📖', 'Read More',   'Batafsil tugmasi', 'channel'),
    ('google_play', 'tg_emoji_google_play', '▶️', 'Google Play', 'Google Play tugmasi', 'channel'),
    ('app_store',   'tg_emoji_app_store',   '🍎', 'App Store',   'App Store tugmasi', 'channel'),
    ('web',         'tg_emoji_web',         '🌐', 'Web',         'Web sayt tugmasi', 'channel'),
    ('bot',         'tg_emoji_bot',         '🤖', 'Bot',         'Telegram Bot tugmasi', 'channel'),
    ('comment',     'tg_emoji_comment',     '💬', 'Comment',     'Komment ko\'rish tugmasi', 'channel'),
    ('server',      'tg_emoji_server',      '🖥', 'Server',      'Server status header', 'monitor'),
    ('cpu',         'tg_emoji_cpu',         '🧠', 'CPU',         'CPU bo\'limi', 'monitor'),
    ('ram',         'tg_emoji_ram',         '💾', 'RAM',         'RAM bo\'limi', 'monitor'),
    ('disk',        'tg_emoji_disk',        '💿', 'Disk',        'Disk bo\'limi', 'monitor'),
    ('ok',          'tg_emoji_ok',          '🟢', 'OK',          'Yashil status (<75%)', 'monitor'),
    ('warn',        'tg_emoji_warn',        '🟡', 'Warning',     'Sariq status (75-90%)', 'monitor'),
    ('critical',    'tg_emoji_critical',    '🔴', 'Critical',    'Qizil status (>90%)', 'monitor'),
    ('chart',       'tg_emoji_chart',       '📊', 'Chart',       'Hisobot header', 'monitor'),
    ('alert',       'tg_emoji_alert',       '🚨', 'Alert',       'CPU alert xabari', 'monitor'),
    ('money',       'tg_emoji_money',       '💰', 'Money',       'Tarif maslahatchi', 'monitor'),
]

CATEGORIES = [
    ('channel', '📢', 'Channel Buttons', 'Kanal postlari inline tugmalaridagi emojilar', '#7c3aed'),
    ('monitor', '🖥', 'Server Monitor', 'Health report va /status xabarlaridagi emojilar', '#10b981'),
]

HARDCODED_EMOJIS = [
    {'emoji': '↩️', 'label': 'Reply', 'used_in': 'Javob xabarnomasi', 'file': 'service.py'},
    {'emoji': '👍', 'label': 'Like', 'used_in': 'Like xabarnomasi', 'file': 'service.py'},
    {'emoji': '👎', 'label': 'Unlike', 'used_in': 'Unlike xabarnomasi', 'file': 'service.py'},
    {'emoji': '📩', 'label': 'Contact', 'used_in': 'Kontakt form logi', 'file': 'service.py'},
    {'emoji': '👤', 'label': 'User', 'used_in': 'Yangi foydalanuvchi', 'file': 'service.py'},
    {'emoji': '🔄', 'label': 'Returning', 'used_in': 'Qaytgan foydalanuvchi', 'file': 'service.py'},
    {'emoji': '⭐️', 'label': 'Premium', 'used_in': 'Premium badge', 'file': 'service.py'},
    {'emoji': '🔍', 'label': 'OSINT', 'used_in': 'OSINT tugmasi', 'file': 'service.py'},
    {'emoji': '🎓', 'label': 'TalabaOvozi', 'used_in': 'TalabaOvozi manba', 'file': 'service.py'},
    {'emoji': '🌐', 'label': 'jaysonkhan', 'used_in': 'Servis ikonkasi', 'file': 'formatters.py'},
    {'emoji': '⚡', 'label': 'nginx', 'used_in': 'Servis ikonkasi', 'file': 'formatters.py'},
    {'emoji': '🐘', 'label': 'postgresql', 'used_in': 'Servis ikonkasi', 'file': 'formatters.py'},
    {'emoji': '🥇🥈🥉', 'label': 'Medals', 'used_in': 'Top processes', 'file': 'formatters.py'},
    {'emoji': '🚫', 'label': 'Ban', 'used_in': '/ban komandasi', 'file': 'webhook.py'},
    {'emoji': '🔇', 'label': 'Mute', 'used_in': '/mute komandasi', 'file': 'webhook.py'},
    {'emoji': '📝', 'label': 'Post', 'used_in': 'Blog post sarlavhasi', 'file': 'channel_share.py'},
    {'emoji': '📱', 'label': 'Project', 'used_in': 'Loyiha sarlavhasi', 'file': 'channel_share.py'},
]


def _ctx(request, extra=None):
    ctx = admin.site.each_context(request)
    ctx.update({'title': 'Telegram Settings', **(extra or {})})
    return ctx


@admin_permission_required('core.change_sitesettings')
def emoji_manager(request):
    site = SiteSettings.load()

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'save_fields':
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

        elif action == 'clear_all':
            update_fields = []
            for _, field, *_ in EMOJI_FIELDS:
                if getattr(site, field, ''):
                    setattr(site, field, '')
                    update_fields.append(field)
            if update_fields:
                site.save(update_fields=update_fields)
                _reset_caches()
                messages.warning(request, 'Barcha emojilar tozalandi.')

    # Build categories
    categories = []
    for cat_key, cat_icon, cat_title, cat_desc, cat_color in CATEGORIES:
        items = []
        cat_filled = 0
        for key, field, fallback, label, desc, cat in EMOJI_FIELDS:
            if cat != cat_key:
                continue
            value = getattr(site, field, '') or ''
            if value:
                cat_filled += 1
            items.append({
                'key': key, 'fallback': fallback, 'label': label,
                'description': desc, 'value': value,
            })
        categories.append({
            'key': cat_key, 'icon': cat_icon, 'title': cat_title,
            'description': cat_desc, 'color': cat_color,
            'items': items, 'filled': cat_filled, 'total': len(items),
        })

    filled = sum(1 for _, f, *_ in EMOJI_FIELDS if getattr(site, f, ''))

    notification_fields = [
        ('Yangi userlar', getattr(site, 'admin_notify_new_users', True)),
        ('Kommentlar', getattr(site, 'admin_notify_comments', True)),
        ('Javoblar', getattr(site, 'admin_notify_replies', True)),
        ('Reaksiyalar', getattr(site, 'admin_notify_reactions', True)),
        ('Likelar', getattr(site, 'admin_notify_likes', True)),
        ('Kontakt xabarlar', getattr(site, 'admin_notify_contacts', True)),
    ]

    return TemplateResponse(request, 'core/emoji_manager.html', _ctx(request, {
        'categories': categories,
        'hardcoded_emojis': HARDCODED_EMOJIS,
        'notification_fields': notification_fields,
        'site': site,
        'stats': {
            'total': len(EMOJI_FIELDS),
            'filled': filled,
            'empty': len(EMOJI_FIELDS) - filled,
        },
    }))


def _reset_caches():
    try:
        from servermonitor.formatters import reset_emoji_cache
        reset_emoji_cache()
    except Exception:
        pass
