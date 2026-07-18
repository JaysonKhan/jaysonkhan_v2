"""
Bot text catalogue — Uzbek (default) + Russian.

Every user-visible @Jaysonkhanbot string lives here as a key with per-language
variants. `t(key, lang, **fmt)` renders one; unknown keys/languages fall back
(ru → uz → the key itself) so a missing translation can never crash a handler.

Language resolution (pref → Telegram client language → uz) lives in
`interactions.notifications.lang` — this module stays pure text.

Conventions:
  - Placeholders are str.format names: {name}. Callers escape() user input
    BEFORE passing it in.
  - Custom emojis (core.emoji.ce) are passed in as placeholders too — the
    catalogue holds no ce() calls.
  - Channel posts (channel_share.py) are single-language content, not bot UI —
    intentionally not here.
"""
from __future__ import annotations

LANGS = ('uz', 'ru')
DEFAULT_LANG = 'uz'

TEXTS: dict[str, dict[str, str]] = {
    # ── Command descriptions (BotFather menu + /start menu, single source) ──
    'cmd.panel': {
        'uz': "Boshqaruv paneli (hammasi bir joyda)",
        'ru': "Панель управления (всё в одном месте)",
    },
    'cmd.ip': {
        'uz': "Admin IP allowlist (barcha saytlar)",
        'ru': "Админ IP-список (все сайты)",
    },
    'cmd.status': {
        'uz': "Server holati (quick snapshot)",
        'ru': "Состояние сервера (быстрый срез)",
    },
    'cmd.services': {
        'uz': "Systemd servislar holati",
        'ru': "Состояние systemd-сервисов",
    },
    'cmd.web': {
        'uz': "Saytlar HTTP health + latency",
        'ru': "HTTP-здоровье сайтов + задержка",
    },
    'cmd.ssl': {
        'uz': "SSL sertifikat muddatlari",
        'ru': "Сроки SSL-сертификатов",
    },
    'cmd.errors': {
        'uz': "Xatoliklar soni (/errors [soat])",
        'ru': "Количество ошибок (/errors [часы])",
    },
    'cmd.disk': {
        'uz': "Disk ishlatilishi (batafsil)",
        'ru': "Использование диска (подробно)",
    },
    'cmd.top': {
        'uz': "Top jarayonlar (CPU/RAM)",
        'ru': "Топ процессов (CPU/RAM)",
    },
    'cmd.db': {
        'uz': "PostgreSQL baza hajmlari",
        'ru': "Размеры баз PostgreSQL",
    },
    'cmd.restart': {
        'uz': "Servis restart (tasdiq bilan)",
        'ru': "Перезапуск сервиса (с подтверждением)",
    },
    'cmd.tariff': {
        'uz': "Contabo tarif tavsiyasi",
        'ru': "Рекомендация по тарифу Contabo",
    },
    'cmd.logs': {
        'uz': "Servis loglari (/logs [servis] [qator])",
        'ru': "Логи сервиса (/logs [сервис] [строки])",
    },
    'cmd.backup': {
        'uz': "PostgreSQL backup yaratish",
        'ru': "Создать бэкап PostgreSQL",
    },
    'cmd.start': {
        'uz': "Botni ishga tushirish",
        'ru': "Запустить бота",
    },
    'cmd.notifications': {
        'uz': "Bildirishnoma sozlamalari",
        'ru': "Настройки уведомлений",
    },
    'cmd.config': {
        'uz': "Admin guruh sozlamalari",
        'ru': "Настройки админ-группы",
    },
    'cmd.lang': {
        'uz': "Til / Язык",
        'ru': "Язык / Til",
    },

    # ── /start ──────────────────────────────────────────────────────────────
    'start.hello': {
        'uz': "{greeting} <b>Salom, Admin!</b>",
        'ru': "{greeting} <b>Здравствуйте, Админ!</b>",
    },
    'start.sec_manage': {'uz': "Boshqaruv", 'ru': "Управление"},
    'start.sec_monitoring': {'uz': "Monitoring", 'ru': "Мониторинг"},
    'start.sec_settings': {'uz': "Sozlamalar", 'ru': "Настройки"},
    'start.sec_auto': {'uz': "Avtomatik", 'ru': "Автоматика"},
    'start.auto_daily': {
        'uz': "Kunlik hisobot — 09:00",
        'ru': "Ежедневный отчёт — 09:00",
    },
    'start.auto_alerts': {
        'uz': "CPU alert — har 10 daq · Disk alert ≥90%",
        'ru': "CPU-алерт — каждые 10 мин · Диск-алерт ≥90%",
    },
    'start.ip_hint': {
        'uz': "IP qo'shish: menga IP yozing yoki jaysonkhan.com/myip",
        'ru': "Добавить IP: пришлите мне IP или откройте jaysonkhan.com/myip",
    },
    'start.user_greeting': {
        'uz': "Salom! Men sizga kommentlaringizga javob kelganda "
              "yoki reaksiya qo'yilganda xabar beraman.\n\n"
              "Sozlamalar: /notifications · Til: /lang",
        'ru': "Здравствуйте! Я сообщу вам, когда на ваш комментарий ответят "
              "или поставят реакцию.\n\n"
              "Настройки: /notifications · Язык: /lang",
    },

    # ── Notifications UI ────────────────────────────────────────────────────
    'notif.not_logged_in': {
        'uz': "Siz hali saytga kirmagansiz. Avval jaysonkhan.com da "
              "Telegram orqali login qiling.",
        'ru': "Вы ещё не заходили на сайт. Сначала войдите на jaysonkhan.com "
              "через Telegram.",
    },
    'notif.header': {
        'uz': "{icon} <b>Bildirishnoma sozlamalari</b>",
        'ru': "{icon} <b>Настройки уведомлений</b>",
    },
    'notif.replies': {'uz': "Javoblar (replies)", 'ru': "Ответы (replies)"},
    'notif.reactions': {'uz': "Reaksiyalar", 'ru': "Реакции"},

    # ── Callback toasts ─────────────────────────────────────────────────────
    'cb.updated': {'uz': "Yangilandi ✓", 'ru': "Обновлено ✓"},
    'cb.no_permission': {'uz': "Ruxsat yo'q", 'ru': "Нет доступа"},
    'cb.profile_not_found': {'uz': "Profil topilmadi", 'ru': "Профиль не найден"},
    'cb.settings_not_found': {'uz': "SiteSettings topilmadi", 'ru': "SiteSettings не найден"},
    'cb.owner_only': {'uz': "🔒 Faqat owner uchun", 'ru': "🔒 Только для владельца"},

    # ── Admin group: ban / mute / config ────────────────────────────────────
    'group.ban_usage': {
        'uz': "{icon} Foydalanuvchi xabariga reply qilib /ban yoki /mute yuboring.",
        'ru': "{icon} Отправьте /ban или /mute ответом (reply) на сообщение пользователя.",
    },
    'group.user_not_identified': {
        'uz': "{icon} Bu xabardan foydalanuvchini aniqlab bo'lmadi.",
        'ru': "{icon} Не удалось определить пользователя по этому сообщению.",
    },
    'group.no_profile': {
        'uz': "{icon} Bu eventda foydalanuvchi profili yo'q.",
        'ru': "{icon} В этом событии нет профиля пользователя.",
    },
    'group.banned': {
        'uz': "{icon} <b>{name}</b> doimiy ban qilindi.",
        'ru': "{icon} <b>{name}</b> заблокирован(а) навсегда.",
    },
    'group.ban_dm': {
        'uz': "{icon} Siz jaysonkhan.com da komment yozishdan doimiy bloklangansiz.",
        'ru': "{icon} Вы навсегда заблокированы от комментирования на jaysonkhan.com.",
    },
    'group.muted': {
        'uz': "{icon} <b>{name}</b> {days} kunga mute qilindi ({until} gacha).",
        'ru': "{icon} <b>{name}</b> отключён(а) на {days} дн. (до {until}).",
    },
    'group.mute_dm': {
        'uz': "{icon} Siz jaysonkhan.com da {days} kunga mute qilindingiz ({until} gacha).",
        'ru': "{icon} Вы отключены от комментирования на jaysonkhan.com на {days} дн. (до {until}).",
    },
    'cfg.header': {
        'uz': "{icon} <b>Admin guruh sozlamalari</b>",
        'ru': "{icon} <b>Настройки админ-группы</b>",
    },
    'cfg.new_users': {'uz': "Yangi userlar", 'ru': "Новые пользователи"},
    'cfg.comments': {'uz': "Kommentlar", 'ru': "Комментарии"},
    'cfg.replies': {'uz': "Javoblar", 'ru': "Ответы"},
    'cfg.reactions': {'uz': "Reaksiyalar", 'ru': "Реакции"},
    'cfg.likes': {'uz': "Likelar", 'ru': "Лайки"},
    'cfg.contacts': {'uz': "Contact xabarlar", 'ru': "Сообщения Contact"},

    # ── Server commands (common) ────────────────────────────────────────────
    'srv.owner_only': {
        'uz': "{icon} Bu komanda faqat server egasi uchun.",
        'ru': "{icon} Эта команда только для владельца сервера.",
    },
    'srv.error': {
        'uz': "{icon} Xatolik: <code>{err}</code>",
        'ru': "{icon} Ошибка: <code>{err}</code>",
    },
    'srv.restarted_toast': {
        'uz': "🔄 {unit} restart qilindi",
        'ru': "🔄 {unit} перезапущен",
    },

    # ── /logs ───────────────────────────────────────────────────────────────
    'logs.unknown': {
        'uz': "{icon} Noma'lum servis: <code>{service}</code>\nMavjud: {available}",
        'ru': "{icon} Неизвестный сервис: <code>{service}</code>\nДоступны: {available}",
    },
    'logs.header': {
        'uz': "{icon} <b>Logs: {service}</b> (oxirgi {n} qator)",
        'ru': "{icon} <b>Логи: {service}</b> (последние {n} строк)",
    },
    'logs.empty': {'uz': "Log topilmadi", 'ru': "Логи не найдены"},
    'logs.truncated': {'uz': "... (kesildi)", 'ru': "... (обрезано)"},
    'logs.no_journalctl': {
        'uz': "{icon} journalctl topilmadi (systemd yo'q)",
        'ru': "{icon} journalctl не найден (нет systemd)",
    },

    # ── /backup ─────────────────────────────────────────────────────────────
    'backup.starting': {
        'uz': "{icon} Backup boshlanmoqda...",
        'ru': "{icon} Начинаю бэкап...",
    },
    'backup.ready': {
        'uz': "{ok} <b>Backup tayyor!</b>\n{folder} <code>{path}</code>\n{disk} Hajm: {size}MB",
        'ru': "{ok} <b>Бэкап готов!</b>\n{folder} <code>{path}</code>\n{disk} Размер: {size}MB",
    },
    'backup.failed': {
        'uz': "{icon} Backup xatolik:\n<pre>{err}</pre>",
        'ru': "{icon} Ошибка бэкапа:\n<pre>{err}</pre>",
    },
    'backup.failed_short': {
        'uz': "❌ Backup xatolik: <code>{err}</code>",
        'ru': "❌ Ошибка бэкапа: <code>{err}</code>",
    },

    # ── /restart ────────────────────────────────────────────────────────────
    'restart.title': {
        'uz': "{icon} <b>Qaysi servis restart qilinsin?</b>\n"
              "(tasdiq so'raladi; infra servislarga /services orqali)",
        'ru': "{icon} <b>Какой сервис перезапустить?</b>\n"
              "(потребуется подтверждение; инфра-сервисы — через /services)",
    },
    'restart.confirm': {
        'uz': "{icon} <code>{unit}</code> restart qilinsinmi?",
        'ru': "{icon} Перезапустить <code>{unit}</code>?",
    },
    'restart.yes_btn': {'uz': "✅ Ha, restart", 'ru': "✅ Да, перезапустить"},
    'restart.cancel_btn': {'uz': "❌ Bekor", 'ru': "❌ Отмена"},
    'restart.unknown': {'uz': "Noma'lum servis", 'ru': "Неизвестный сервис"},
    'restart.cancelled': {'uz': "Bekor qilindi", 'ru': "Отменено"},
    'restart.starting_toast': {'uz': "🔄 {unit} restart...", 'ru': "🔄 {unit} перезапуск..."},
    'restart.done': {
        'uz': "{icon} <code>{unit}</code> restart yakunlandi — holat: <code>{state}</code>",
        'ru': "{icon} Перезапуск <code>{unit}</code> завершён — статус: <code>{state}</code>",
    },
    'restart.fail': {
        'uz': "{icon} Restart xato: <code>{err}</code>",
        'ru': "{icon} Ошибка перезапуска: <code>{err}</code>",
    },
    'restart.warn_edustats': {
        'uz': "⚠️ edustats-bot restartdan 60s keyin uzbmb FULL sync boshlanadi — "
              "edustats.uz ~10 daqiqa sekinlashadi/000 beradi (o'zi tiklanadi, "
              "qayta restart QILMANG).",
        'ru': "⚠️ Через 60с после рестарта edustats-bot начнётся FULL-синк uzbmb — "
              "edustats.uz будет тормозить/отдавать 000 ~10 минут (восстановится сам, "
              "повторно НЕ перезапускайте).",
    },

    # ── /panel ──────────────────────────────────────────────────────────────
    'panel.title': {
        'uz': "{icon} <b>Boshqaruv paneli</b>\nKerakli bo'limni tanlang:",
        'ru': "{icon} <b>Панель управления</b>\nВыберите раздел:",
    },
    'panel.b_status': {'uz': "📊 Status", 'ru': "📊 Статус"},
    'panel.b_services': {'uz': "🔧 Servislar", 'ru': "🔧 Сервисы"},
    'panel.b_web': {'uz': "🌐 Web", 'ru': "🌐 Web"},
    'panel.b_ssl': {'uz': "🔐 SSL", 'ru': "🔐 SSL"},
    'panel.b_errors': {'uz': "🧾 Errorlar", 'ru': "🧾 Ошибки"},
    'panel.b_disk': {'uz': "💿 Disk", 'ru': "💿 Диск"},
    'panel.b_top': {'uz': "🏆 Top", 'ru': "🏆 Топ"},
    'panel.b_db': {'uz': "🐘 DB", 'ru': "🐘 БД"},
    'panel.b_ip': {'uz': "🛡 IP Allowlist", 'ru': "🛡 IP-список"},
    'panel.b_restart': {'uz': "🔄 Restart", 'ru': "🔄 Перезапуск"},

    # ── /ip (allowlist) ─────────────────────────────────────────────────────
    'ip.panel_title': {
        'uz': "{icon} <b>Admin IP Allowlist</b> — barcha saytlar",
        'ru': "{icon} <b>Админ IP Allowlist</b> — все сайты",
    },
    'ip.dynamic_header': {
        'uz': "{icon} <b>Dinamik (bot boshqaradi, restart kerak emas):</b>",
        'ru': "{icon} <b>Динамические (управляет бот, рестарт не нужен):</b>",
    },
    'ip.empty': {
        'uz': "<i>bo'sh — hali IP qo'shilmagan</i>",
        'ru': "<i>пусто — IP ещё не добавлены</i>",
    },
    'ip.env_header': {
        'uz': "{icon} <b>.env bazaviy ro'yxatlar</b> (faqat ma'lumot):",
        'ru': "{icon} <b>Базовые списки из .env</b> (только для сведения):",
    },
    'ip.env_empty': {'uz': "bo'sh", 'ru': "пусто"},
    'ip.env_unreadable': {'uz': "o'qib bo'lmadi", 'ru': "не удалось прочитать"},
    'ip.history_header': {
        'uz': "{icon} <b>So'nggi o'zgarishlar:</b>",
        'ru': "{icon} <b>Последние изменения:</b>",
    },
    'ip.footer': {
        'uz': "{icon} Yangi IP <b>bir zumda</b> jaysonkhan + uzexam + edustats "
              "admin panellariga tarqaladi. .env fayllarga tegilmaydi.",
        'ru': "{icon} Новый IP применяется <b>мгновенно</b> в админках jaysonkhan + "
              "uzexam + edustats. Файлы .env не трогаются.",
    },
    'ip.btn_add': {'uz': "➕ IP qo'shish", 'ru': "➕ Добавить IP"},
    'ip.btn_del': {'uz': "🗑 O'chirish", 'ru': "🗑 Удалить"},
    'ip.btn_detect': {'uz': "🌍 IP manzilimni aniqlash", 'ru': "🌍 Определить мой IP"},
    'ip.btn_refresh': {'uz': "🔄 Yangilash", 'ru': "🔄 Обновить"},
    'ip.btn_back': {'uz': "⬅️ Orqaga", 'ru': "⬅️ Назад"},
    'ip.btn_confirm_add': {'uz': "✅ Qo'shish", 'ru': "✅ Добавить"},
    'ip.btn_cancel': {'uz': "❌ Bekor", 'ru': "❌ Отмена"},
    'ip.btn_confirm_del': {'uz': "✅ Ha, o'chir", 'ru': "✅ Да, удалить"},
    'ip.note': {'uz': " (izoh: {label})", 'ru': " (метка: {label})"},
    'ip.confirm_add': {
        'uz': "{icon} <code>{ip}</code>{note} barcha saytlarning admin "
              "allowlist'iga qo'shilsinmi?",
        'ru': "{icon} Добавить <code>{ip}</code>{note} в админ-allowlist "
              "всех сайтов?",
    },
    'ip.addhelp': {
        'uz': "{icon} <b>IP qo'shish yo'llari:</b>\n\n"
              "1. Menga IP manzilni oddiy xabar qilib yuboring — "
              "masalan <code>84.54.12.7</code>\n"
              "2. <code>/ip add 84.54.12.7 uy-wifi</code> (izoh ixtiyoriy)\n"
              "3. <a href=\"{url}\">jaysonkhan.com/myip</a> sahifasini oching — "
              "IP'ingizni ko'rsatadi va bir bosishda botga qaytaradi.\n\n"
              "Har qanday yo'lda ham men tasdiq so'rayman.",
        'ru': "{icon} <b>Как добавить IP:</b>\n\n"
              "1. Просто пришлите мне IP-адрес сообщением — "
              "например <code>84.54.12.7</code>\n"
              "2. <code>/ip add 84.54.12.7 дом-wifi</code> (метка необязательна)\n"
              "3. Откройте <a href=\"{url}\">jaysonkhan.com/myip</a> — страница "
              "покажет ваш IP и в один тап вернёт его боту.\n\n"
              "В любом случае я запрошу подтверждение.",
    },
    'ip.delmenu_title': {
        'uz': "{icon} <b>Qaysi IP o'chirilsin?</b>\n(.env bazaviy IP'lariga tegilmaydi)",
        'ru': "{icon} <b>Какой IP удалить?</b>\n(базовые IP из .env не трогаются)",
    },
    'ip.delmenu_empty': {'uz': "Dinamik ro'yxat bo'sh", 'ru': "Динамический список пуст"},
    'ip.confirm_del': {
        'uz': "{icon} <code>{ip}</code> barcha saytlar allowlist'idan o'chirilsinmi?",
        'ru': "{icon} Удалить <code>{ip}</code> из allowlist всех сайтов?",
    },
    'ip.added': {
        'uz': "{icon} <code>{ip}</code> qo'shildi — jaysonkhan, uzexam va edustats "
              "admin panellarida darhol amal qiladi.",
        'ru': "{icon} <code>{ip}</code> добавлен — сразу действует в админках "
              "jaysonkhan, uzexam и edustats.",
    },
    'ip.deleted': {
        'uz': "{icon} <code>{ip}</code> o'chirildi.",
        'ru': "{icon} <code>{ip}</code> удалён.",
    },
    'ip.toast_added': {'uz': "✓ Qo'shildi", 'ru': "✓ Добавлен"},
    'ip.toast_deleted': {'uz': "✓ O'chirildi", 'ru': "✓ Удалён"},
    'ip.toast_error': {'uz': "Xatolik", 'ru': "Ошибка"},
    'ip.toast_bad_ip': {'uz': "IP o'qilmadi", 'ru': "IP не распознан"},
    'ip.link_bad': {
        'uz': "{icon} Havoladagi IP o'qilmadi.",
        'ru': "{icon} Не удалось прочитать IP из ссылки.",
    },
    'ip.invalid': {
        'uz': "{icon} Noto'g'ri IP: <code>{raw}</code>",
        'ru': "{icon} Неверный IP: <code>{raw}</code>",
    },
    # allowed_ips lib result codes
    'ip.err_invalid': {'uz': "Noto'g'ri IP: {raw}", 'ru': "Неверный IP: {raw}"},
    'ip.err_duplicate': {'uz': "{ip} allaqachon ro'yxatda.", 'ru': "{ip} уже в списке."},
    'ip.err_full': {
        'uz': "Ro'yxat to'la ({max} ta) — avval eskisini o'chiring.",
        'ru': "Список полон ({max}) — сначала удалите старый IP.",
    },
    'ip.err_write': {'uz': "Yozib bo'lmadi: {err}", 'ru': "Не удалось записать: {err}"},
    'ip.err_not_found': {
        'uz': "{ip} dinamik ro'yxatda yo'q (.env bazasini bot boshqarmaydi).",
        'ru': "{ip} нет в динамическом списке (базой из .env бот не управляет).",
    },

    # ── Report sections (formatters) ────────────────────────────────────────
    'rep.title': {'uz': "<b>Server Health Report</b>", 'ru': "<b>Отчёт о состоянии сервера</b>"},
    'rep.uptime': {'uz': "Uptime: <b>{up}</b>", 'ru': "Аптайм: <b>{up}</b>"},
    'rep.cores': {'uz': "({n} cores)", 'ru': "({n} ядер)"},
    'rep.core': {'uz': "Core {i}", 'ru': "Ядро {i}"},
    'rep.services': {'uz': "<b>Services</b>", 'ru': "<b>Сервисы</b>"},
    'rep.swap_none': {'uz': "<b>Swap</b>: not configured", 'ru': "<b>Swap</b>: не настроен"},
    'rep.free': {'uz': "free", 'ru': "свободно"},
    'rep.top_procs': {'uz': "<b>Top Processes (CPU)</b>", 'ru': "<b>Топ процессов (CPU)</b>"},
    'rep.cron': {'uz': "<b>Cron (24h)</b>", 'ru': "<b>Cron (24ч)</b>"},
    'rep.cron_line': {
        'uz': "{ok} {n_ok} muvaffaqiyat · {bad} {n_bad} xato",
        'ru': "{ok} {n_ok} успешно · {bad} {n_bad} с ошибкой",
    },
    'rep.cron_overdue': {'uz': "⏳ Overdue: {n} ta", 'ru': "⏳ Просрочено: {n}"},
    'rep.down': {'uz': "🚨 <b>Down services:</b> {list}", 'ru': "🚨 <b>Лежащие сервисы:</b> {list}"},

    # ── Service group labels ────────────────────────────────────────────────
    'grp.apps': {'uz': "Ilovalar", 'ru': "Приложения"},
    'grp.infra': {'uz': "Infratuzilma", 'ru': "Инфраструктура"},
    'grp.mail': {'uz': "Mail Server", 'ru': "Почтовый сервер"},
    'grp.security': {'uz': "Xavfsizlik", 'ru': "Безопасность"},
    'rep.up': {'uz': "({a}/{b} ishlayapti)", 'ru': "({a}/{b} работают)"},

    # ── Alerts ──────────────────────────────────────────────────────────────
    'alert.cpu_title': {
        'uz': "{icon} <b>CPU Alert!</b> {hot}/{total} cores above {thr}%\n",
        'ru': "{icon} <b>CPU-алерт!</b> {hot}/{total} ядер выше {thr}%\n",
    },
    'alert.cpu_advice': {
        'uz': "\n⚠️ <b>Server kuchaytirish kerak bo'lishi mumkin!</b>\n"
              "CPU overload — ko'proq yadro yoki kuchliroq protsessor tavsiya etiladi.",
        'ru': "\n⚠️ <b>Возможно, серверу нужно больше ресурсов!</b>\n"
              "Перегрузка CPU — рекомендуется больше ядер или более мощный процессор.",
    },
    'alert.svc_down_title': {'uz': "🚨 <b>Service DOWN</b>", 'ru': "🚨 <b>Сервис УПАЛ</b>"},
    'alert.svc_down_body': {
        'uz': "{icon} <b>{display}</b> — endi ishlamayapti.",
        'ru': "{icon} <b>{display}</b> — больше не работает.",
    },
    'alert.svc_down_action': {
        'uz': "Tekshirish:\n  <code>journalctl -u {unit} -n 50</code>\n"
              "  <code>systemctl status {unit}</code>\n\n"
              "Koʼp marta DOWN boʼlsa restart yoki deploy.sh bilan qayta koʼtarish kerak.",
        'ru': "Проверка:\n  <code>journalctl -u {unit} -n 50</code>\n"
              "  <code>systemctl status {unit}</code>\n\n"
              "Если падает многократно — нужен restart или повторный deploy.sh.",
    },
    'alert.svc_up_title': {'uz': "✅ <b>Service Recovered</b>", 'ru': "✅ <b>Сервис восстановлен</b>"},
    'alert.svc_up_body': {
        'uz': "{icon} <b>{display}</b> — qayta ishlayapti.",
        'ru': "{icon} <b>{display}</b> — снова работает.",
    },
    'alert.svc_up_action': {
        'uz': "Avtomatik tiklandi yoki deploy/restart natijasi.",
        'ru': "Восстановился автоматически или в результате deploy/restart.",
    },
    'alert.svc_group': {'uz': "Guruh", 'ru': "Группа"},
    'alert.svc_state': {'uz': "Holat", 'ru': "Статус"},
    'alert.cron_title': {'uz': "🚨 <b>Cron Health Alert</b>", 'ru': "🚨 <b>Алерт: здоровье cron</b>"},
    'alert.cron_failed': {'uz': "\n❌ <b>Failed runs ({n})</b>", 'ru': "\n❌ <b>Неудачные запуски ({n})</b>"},
    'alert.cron_more': {'uz': "  …va yana {n} ta", 'ru': "  …и ещё {n}"},
    'alert.cron_overdue': {
        'uz': "\n⏳ <b>Overdue (no recent run)</b>",
        'ru': "\n⏳ <b>Просроченные (давно не запускались)</b>",
    },
    'alert.cron_last': {'uz': "last: {last}", 'ru': "последний: {last}"},
    'alert.disk_title': {'uz': "🚨 <b>Disk Alert!</b>", 'ru': "🚨 <b>Диск-алерт!</b>"},
    'alert.disk_advice': {
        'uz': "\nJoy bo'shatish: eski backuplar, <code>journalctl --vacuum-time=7d</code>, "
              "<code>apt clean</code>. Tekshirish: /disk",
        'ru': "\nОсвободить место: старые бэкапы, <code>journalctl --vacuum-time=7d</code>, "
              "<code>apt clean</code>. Проверка: /disk",
    },
    'alert.ssl_header': {
        'uz': "\n\n🔐 <b>SSL ogohlantirish!</b> (yangilash QO'LDA — DNS-01)",
        'ru': "\n\n🔐 <b>SSL-предупреждение!</b> (продление ВРУЧНУЮ — DNS-01)",
    },
    'alert.ssl_fail_line': {
        'uz': "  🔴 {domain} — tekshirib bo'lmadi ({err})",
        'ru': "  🔴 {domain} — не удалось проверить ({err})",
    },
    'alert.ssl_days_line': {
        'uz': "  ⏳ {domain} — <b>{d} kun qoldi</b> ({exp})",
        'ru': "  ⏳ {domain} — <b>осталось {d} дн.</b> ({exp})",
    },

    # ── /web ────────────────────────────────────────────────────────────────
    'web.title': {'uz': "{icon} <b>Web Health</b> (HTTP)", 'ru': "{icon} <b>Web-здоровье</b> (HTTP)"},
    'web.internal': {
        'uz': "\n  {icon} <i>Ichki API (localhost):</i>",
        'ru': "\n  {icon} <i>Внутренние API (localhost):</i>",
    },
    'web.no_conn': {
        'uz': "  🔴 <b>{label}</b> — ulanish yo'q ({err})",
        'ru': "  🔴 <b>{label}</b> — нет соединения ({err})",
    },

    # ── /ssl ────────────────────────────────────────────────────────────────
    'ssl.title': {'uz': "{icon} <b>SSL sertifikatlar</b>", 'ru': "{icon} <b>SSL-сертификаты</b>"},
    'ssl.fail': {
        'uz': "  🔴 <b>{domain}</b> — tekshirib bo'lmadi ({err})",
        'ru': "  🔴 <b>{domain}</b> — не удалось проверить ({err})",
    },
    'ssl.crit': {
        'uz': "  🔴 <b>{domain}</b> — <b>{d} kun qoldi!</b> ({exp})",
        'ru': "  🔴 <b>{domain}</b> — <b>осталось {d} дн.!</b> ({exp})",
    },
    'ssl.warn': {
        'uz': "  🟡 <b>{domain}</b> — {d} kun qoldi ({exp})",
        'ru': "  🟡 <b>{domain}</b> — осталось {d} дн. ({exp})",
    },
    'ssl.ok': {
        'uz': "  🟢 <b>{domain}</b> — {d} kun ({exp})",
        'ru': "  🟢 <b>{domain}</b> — {d} дн. ({exp})",
    },
    'ssl.footer': {
        'uz': "\n{icon} Yangilash qo'lda (DNS-01): <code>certbot renew</code> yo'q — "
              "muddat yaqinlashsa alert keladi.",
        'ru': "\n{icon} Продление вручную (DNS-01): <code>certbot renew</code> нет — "
              "при приближении срока придёт алерт.",
    },

    # ── /errors ─────────────────────────────────────────────────────────────
    'err.title': {
        'uz': "{icon} <b>Xatoliklar</b> (oxirgi {h} soat, journalctl)",
        'ru': "{icon} <b>Ошибки</b> (за {h} ч, journalctl)",
    },
    'err.count': {'uz': "{n} ta", 'ru': "{n} шт."},
    'err.worst': {
        'uz': "\nEng ko'p xato — <code>{unit}</code>, oxirgisi:",
        'ru': "\nБольше всего ошибок — <code>{unit}</code>, последняя:",
    },
    'err.clean': {'uz': "\n{icon} Hammasi toza!", 'ru': "\n{icon} Всё чисто!"},
    'err.details': {
        'uz': "\nBatafsil: <code>/logs [servis] [qator]</code>",
        'ru': "\nПодробнее: <code>/logs [сервис] [строки]</code>",
    },
    'err.na': {'uz': "journalctl yo'q", 'ru': "нет journalctl"},

    # ── /db ─────────────────────────────────────────────────────────────────
    'db.conns': {
        'uz': "\n  🔌 Aktiv ulanishlar: <b>{n}</b>",
        'ru': "\n  🔌 Активные подключения: <b>{n}</b>",
    },

    # ── /tariff ─────────────────────────────────────────────────────────────
    'tariff.title': {
        'uz': "{icon} <b>Contabo Tariff Advisor</b>\n",
        'ru': "{icon} <b>Советник по тарифу Contabo</b>\n",
    },
    'tariff.current': {'uz': "{icon} Joriy: <b>{name}</b>", 'ru': "{icon} Текущий: <b>{name}</b>"},
    'tariff.rec': {'uz': "{icon} <b>Tavsiya: {rec}</b>", 'ru': "{icon} <b>Рекомендация: {rec}</b>"},
    'tariff.reason_upgrade': {
        'uz': "Resurlar limitga yaqinlashmoqda",
        'ru': "Ресурсы приближаются к лимиту",
    },
    'tariff.reason_downgrade': {
        'uz': "Resurslar kam ishlatilmoqda — tejash mumkin",
        'ru': "Ресурсы используются слабо — можно сэкономить",
    },
    'tariff.reason_keep': {'uz': "Hozirgi plan optimal", 'ru': "Текущий план оптимален"},
    'tariff.suggested': {
        'uz': "\n{icon} Tavsiya etilgan plan: <b>{name}</b>",
        'ru': "\n{icon} Рекомендуемый план: <b>{name}</b>",
    },
    'tariff.extra': {'uz': "   💸 +€{diff}/mo qo'shimcha", 'ru': "   💸 +€{diff}/мес доплата"},
    'tariff.save': {'uz': "   💰 €{diff}/mo tejash!", 'ru': "   💰 Экономия €{diff}/мес!"},

    # ── Monthly log report ──────────────────────────────────────────────────
    'mon.title': {
        'uz': "📋 <b>Oylik log hisoboti — {period}</b>",
        'ru': "📋 <b>Месячный отчёт по логам — {period}</b>",
    },
    'mon.healthy': {'uz': "✅ Server sog‘lom", 'ru': "✅ Сервер здоров"},
    'mon.attention': {'uz': "⚠️ Diqqat: real xatolar bor", 'ru': "⚠️ Внимание: есть реальные ошибки"},
    'mon.5xx': {'uz': "🔴 <b>5xx (real xatolar):</b> {n}", 'ru': "🔴 <b>5xx (реальные ошибки):</b> {n}"},
    'mon.blocked': {'uz': "🛡 <b>Bloklangan skanerlar:</b> {n}", 'ru': "🛡 <b>Заблокированные сканеры:</b> {n}"},
    'mon.total': {
        'uz': "📊 <b>Jami:</b> real ERROR {e} · WARNING {w}",
        'ru': "📊 <b>Всего:</b> реальных ERROR {e} · WARNING {w}",
    },
    'mon.top_errors': {'uz': "🔎 <b>Top server xatolari:</b>", 'ru': "🔎 <b>Топ ошибок сервера:</b>"},
    'mon.archived': {
        'uz': "<i>Loglar arxivlandi va tozalandi. {span}{n} qator.</i>",
        'ru': "<i>Логи заархивированы и очищены. {span}{n} строк.</i>",
    },
    'mon.top_paths': {'uz': "🎯 <b>Eng ko‘p urinilgan yo‘llar:</b>", 'ru': "🎯 <b>Самые атакуемые пути:</b>"},
    'mon.scanner_ips': {'uz': "🌐 <b>Faol skaner IP‘lari:</b>", 'ru': "🌐 <b>Активные IP сканеров:</b>"},

    # ── User notifications (site events → DM) ───────────────────────────────
    'ntf.reply': {
        'uz': "{icon} <b>{name}</b> sizning kommentingizga javob yozdi:\n\n\"{snippet}\"",
        'ru': "{icon} <b>{name}</b> ответил(а) на ваш комментарий:\n\n\"{snippet}\"",
    },
    'ntf.reply_btn': {'uz': "Javob berish", 'ru': "Ответить"},

    # ── Admin-group event log ───────────────────────────────────────────────
    'adm.comment': {
        'uz': "{icon} <b>{name}</b> komment yozdi:",
        'ru': "{icon} <b>{name}</b> написал(а) комментарий:",
    },
    'adm.view_comment': {'uz': "Kommentni ko'rish", 'ru': "Открыть комментарий"},
    'adm.view_reply': {'uz': "Javobni ko'rish", 'ru': "Открыть ответ"},
    'adm.reaction_added': {
        'uz': "{emoji} <b>{actor}</b> — <b>{author}</b> kommentiga reaksiya qo'ydi",
        'ru': "{emoji} <b>{actor}</b> — реакция на комментарий <b>{author}</b>",
    },
    'adm.reaction_removed': {
        'uz': "{emoji} <b>{actor}</b> — <b>{author}</b> kommentidan reaksiyani olib tashladi",
        'ru': "{emoji} <b>{actor}</b> — убрал(а) реакцию с комментария <b>{author}</b>",
    },
    'adm.liked': {
        'uz': "{emoji} <b>{actor}</b> yoqtirdi: <b>{title}</b>",
        'ru': "{emoji} <b>{actor}</b> поставил(а) лайк: <b>{title}</b>",
    },
    'adm.unliked': {
        'uz': "{emoji} <b>{actor}</b> like olib tashladi: <b>{title}</b>",
        'ru': "{emoji} <b>{actor}</b> убрал(а) лайк: <b>{title}</b>",
    },
    'adm.view': {'uz': "Ko'rish", 'ru': "Открыть"},
    'adm.new_entity': {
        'uz': "{emoji} <b>Yangi {type}: {name}</b>",
        'ru': "{emoji} <b>Новый {type}: {name}</b>",
    },
    'adm.type_user': {'uz': "foydalanuvchi", 'ru': "пользователь"},
    'adm.type_bot': {'uz': "bot", 'ru': "бот"},
    'adm.type_group': {'uz': "guruh", 'ru': "группа"},
    'adm.type_supergroup': {'uz': "superguruh", 'ru': "супергруппа"},
    'adm.type_channel': {'uz': "kanal", 'ru': "канал"},
    'adm.type_unknown': {'uz': "noma'lum", 'ru': "неизвестно"},
    'adm.src_site': {'uz': "{icon} Sayt (Login)", 'ru': "{icon} Сайт (логин)"},
    'adm.src_site_action': {'uz': "{icon} Saytga kirdi", 'ru': "{icon} Вошёл на сайт"},
    'adm.src_found': {'uz': "{s} dan topildi", 'ru': "найден через {s}"},
    'adm.badge_verified': {'uz': "Tasdiqlangan", 'ru': "Подтверждён"},
    'adm.contact_new': {
        'uz': "{icon} Yangi xabar:\n<b>Kimdan:</b> {name} ({email})\n"
              "<b>Mavzu:</b> {subject}\n<b>Xabar:</b> {body}",
        'ru': "{icon} Новое сообщение:\n<b>От:</b> {name} ({email})\n"
              "<b>Тема:</b> {subject}\n<b>Сообщение:</b> {body}",
    },
    'adm.contact_open': {'uz': "Admin panelda ko'rish", 'ru': "Открыть в админке"},
    'adm.btn_site': {'uz': "🌐 Sayt", 'ru': "🌐 Сайт"},

    # ── /lang ───────────────────────────────────────────────────────────────
    'lang.choose': {
        'uz': "🌐 Til tanlang / Выберите язык:",
        'ru': "🌐 Выберите язык / Til tanlang:",
    },
    'lang.saved': {
        'uz': "✅ Til: O'zbekcha. Menyu yangilandi — /start",
        'ru': "✅ Язык: Русский. Меню обновлено — /start",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **fmt) -> str:
    """Render a catalogue string; falls back ru→uz→key, never raises."""
    entry = TEXTS.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return text
    return text
