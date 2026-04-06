"""
Telegram Settings — manage ALL 58 custom emoji IDs.
"""
from __future__ import annotations

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from core.decorators import admin_permission_required
from core.models import SiteSettings

EMOJI_FIELDS = [
    # Channel & Sharing (9)
    ('read_more',   'tg_emoji_read_more',   '📖', 'Read More',    'Batafsil tugmasi', 'channel'),
    ('google_play', 'tg_emoji_google_play', '▶️', 'Google Play',  'Google Play tugmasi', 'channel'),
    ('app_store',   'tg_emoji_app_store',   '🍎', 'App Store',    'App Store tugmasi', 'channel'),
    ('web',         'tg_emoji_web',         '🌐', 'Web',          'Web sayt tugmasi', 'channel'),
    ('bot',         'tg_emoji_bot',         '🤖', 'Bot',          'Telegram Bot tugmasi', 'channel'),
    ('comment',     'tg_emoji_comment',     '💬', 'Comment',      'Komment tugmasi + xabar soni', 'channel'),
    ('post',        'tg_emoji_post',        '📝', 'Post',         'Blog post caption', 'channel'),
    ('project',     'tg_emoji_project',     '📱', 'Project',      'Loyiha caption', 'channel'),
    ('tech',        'tg_emoji_tech',        '🛠', 'Tech Stack',   'Texnologiyalar', 'channel'),

    # Server Monitor (22)
    ('server',        'tg_emoji_server',        '🖥', 'Server',       'Server header', 'monitor'),
    ('cpu',           'tg_emoji_cpu',           '🧠', 'CPU',          'CPU bo\'limi', 'monitor'),
    ('ram',           'tg_emoji_ram',           '💾', 'RAM',          'RAM bo\'limi', 'monitor'),
    ('disk',          'tg_emoji_disk',          '💿', 'Disk',         'Disk bo\'limi', 'monitor'),
    ('ok',            'tg_emoji_ok',            '🟢', 'OK',           'Yashil status', 'monitor'),
    ('warn',          'tg_emoji_warn',          '🟡', 'Warning',      'Sariq status', 'monitor'),
    ('critical',      'tg_emoji_critical',      '🔴', 'Critical',     'Qizil status', 'monitor'),
    ('chart',         'tg_emoji_chart',         '📊', 'Chart',        'Hisobot header', 'monitor'),
    ('alert',         'tg_emoji_alert',         '🚨', 'Alert',        'CPU alert', 'monitor'),
    ('money',         'tg_emoji_money',         '💰', 'Money',        'Tarif maslahatchi', 'monitor'),
    ('clock',         'tg_emoji_clock',         '🕐', 'Clock',        'Vaqt ko\'rsatish', 'monitor'),
    ('uptime',        'tg_emoji_uptime',        '⏱', 'Uptime',       'Server uptime', 'monitor'),
    ('load',          'tg_emoji_load',          '📈', 'Load',         'CPU load average', 'monitor'),
    ('swap',          'tg_emoji_swap',          '🔄', 'Swap',         'Swap bo\'limi', 'monitor'),
    ('services_icon', 'tg_emoji_services_icon', '🔧', 'Services',     'Servislar bo\'limi', 'monitor'),
    ('trophy',        'tg_emoji_trophy',        '🏆', 'Trophy',       'Top processlar', 'monitor'),
    ('nginx',         'tg_emoji_nginx',         '⚡', 'nginx',        'nginx servis icon', 'monitor'),
    ('postgresql',    'tg_emoji_postgresql',    '🐘', 'PostgreSQL',   'PostgreSQL servis icon', 'monitor'),
    ('package',       'tg_emoji_package',       '📦', 'Package',      'Contabo plan', 'monitor'),
    ('upgrade',       'tg_emoji_upgrade',       '⬆️', 'Upgrade',      'Upgrade tavsiya', 'monitor'),
    ('downgrade',     'tg_emoji_downgrade',     '⬇️', 'Downgrade',    'Downgrade tavsiya', 'monitor'),

    # Notifications (4)
    ('reply',       'tg_emoji_reply',       '↩️', 'Reply',        'Javob xabarnomasi', 'notify'),
    ('like',        'tg_emoji_like',        '👍', 'Like',         'Like xabarnomasi', 'notify'),
    ('unlike',      'tg_emoji_unlike',      '👎', 'Unlike',       'Unlike xabarnomasi', 'notify'),
    ('contact_msg', 'tg_emoji_contact_msg', '📩', 'Contact',      'Kontakt form logi', 'notify'),

    # Admin Log (16)
    ('user',          'tg_emoji_user',          '👤', 'User',         'Yangi foydalanuvchi', 'admin_log'),
    ('returning',     'tg_emoji_returning',     '🔄', 'Returning',    'Qaytgan foydalanuvchi', 'admin_log'),
    ('premium',       'tg_emoji_premium',       '⭐️', 'Premium',     'Premium badge', 'admin_log'),
    ('osint',         'tg_emoji_osint',         '🔍', 'OSINT',        'OSINT tugmasi', 'admin_log'),
    ('education',     'tg_emoji_education',     '🎓', 'Education',    'TalabaOvozi manba', 'admin_log'),
    ('group',         'tg_emoji_group',         '👥', 'Group',        'Group/supergroup', 'admin_log'),
    ('channel_icon',  'tg_emoji_channel_icon',  '📢', 'Channel',      'Channel entity', 'admin_log'),
    ('id_badge',      'tg_emoji_id_badge',      '🆔', 'ID Badge',     'Telegram ID', 'admin_log'),
    ('phone',         'tg_emoji_phone',         '📱', 'Phone',        'Telefon raqami', 'admin_log'),
    ('sources',       'tg_emoji_sources',       '📡', 'Sources',      'Servis manbalari', 'admin_log'),
    ('crown',         'tg_emoji_crown',         '👑', 'Crown',        'Admin soni', 'admin_log'),
    ('verified',      'tg_emoji_verified',      '✅', 'Verified',     'Tasdiqlangan badge', 'admin_log'),
    ('scam_warn',     'tg_emoji_scam_warn',     '⚠️', 'SCAM',        'SCAM ogohlantirish', 'admin_log'),
    ('history',       'tg_emoji_history',       '📝', 'History',      'Username tarix', 'admin_log'),
    ('pencil',        'tg_emoji_pencil',        '✏️', 'Pencil',       'Ism tarix', 'admin_log'),
    ('calendar',      'tg_emoji_calendar',      '📅', 'Calendar',     'Faollik davri', 'admin_log'),

    # Bot Commands (10)
    ('greeting',           'tg_emoji_greeting',           '👋', 'Greeting',      '/start salomi', 'command'),
    ('ban',                'tg_emoji_ban',                '🚫', 'Ban',           '/ban komandasi', 'command'),
    ('mute',               'tg_emoji_mute',               '🔇', 'Mute',          '/mute komandasi', 'command'),
    ('lock',               'tg_emoji_lock',               '🔒', 'Lock',          'Cheklangan kirish', 'command'),
    ('notifications_icon', 'tg_emoji_notifications_icon', '🔔', 'Notifications', 'Bildirishnomalar header', 'command'),
    ('config_icon',        'tg_emoji_config_icon',        '⚙️', 'Config',        'Sozlamalar header', 'command'),
    ('error',              'tg_emoji_error',              '❌', 'Error',          'Xatolik xabarlari', 'command'),
    ('success',            'tg_emoji_success',            '✅', 'Success',        'Muvaffaqiyat xabarlari', 'command'),
    ('backup_icon',        'tg_emoji_backup_icon',        '💾', 'Backup',         'Backup komandasi', 'command'),
    ('logs_icon',          'tg_emoji_logs_icon',          '📋', 'Logs',           'Loglar komandasi', 'command'),
]

CATEGORIES = [
    ('channel',   '📢', 'Channel & Sharing',  'Kanal postlari, inline tugmalar', '#7c3aed'),
    ('monitor',   '🖥', 'Server Monitor',     'Health report, /status, tariff', '#10b981'),
    ('notify',    '🔔', 'Notifications',      'Like, reply, contact xabarnomalar', '#3b82f6'),
    ('admin_log', '👤', 'Admin Log',          'Yangi user, badge, stats emojilar', '#f59e0b'),
    ('command',   '⚡', 'Bot Commands',       '/start, /ban, /config javoblari', '#ef4444'),
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
        return redirect('telegram_settings')

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
        from core.emoji import reset_cache
        reset_cache()
    except Exception:
        pass
