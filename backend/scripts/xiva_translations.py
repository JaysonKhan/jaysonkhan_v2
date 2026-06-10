"""One-shot: force-set XIVA INK v4 UI translations in locale/*/django.po.

Copy source: jaysonkhan-v4 design handoff (js/i18n.jsx). Overwrites the listed
msgids in xo/uz/ru/en, clearing any fuzzy flags gettext guessed wrong.

Run from backend/:  venv/bin/python scripts/xiva_translations.py
Then:               venv/bin/python manage.py compilemessages -l xo -l uz -l ru -l en
"""
import polib

# msgid -> (xo, uz, ru, en)  — en empty string means "fall back to msgid"
T = {
    # Nav / footer
    'Home': ("Bosh bet", "Bosh sahifa", "Главная", ""),
    'Work': ("Ishlar", "Loyihalar", "Проекты", ""),
    'Journal': ("Jurnal", "Jurnal", "Журнал", ""),
    'Team': ("Jamoa", "Jamoa", "Команда", ""),
    'Contact': ("Aloqa", "Aloqa", "Контакт", ""),
    'Hire the studio': ("Gal, ishlashamiz", "Hamkorlik", "Сотрудничество", ""),

    # Home
    'Start a project': ("Loyiha boshlaymizmi?", "Loyiha boshlash", "Начать проект", ""),
    'View case studies': ("Ishlarga qarang", "Case study'lar", "Кейсы", ""),
    'Career · Track record': ("Karyera · Iz", "Karyera · Tarix", "Карьера · История", ""),
    "Where I've shipped.": ("Qayerlarda yetkazganman.", "Qayerlarda yetkazganman.", "Где я доставлял.", ""),
    'PRESENT': ("HOZIR", "HOZIR", "СЕЙЧАС", ""),
    '04 — Selected work': ("04 — Saralangan ishlar", "04 — Saralangan ishlar", "04 — Избранные работы", ""),
    'View all projects': ("Hamma loyihalar", "Barcha loyihalar", "Все проекты", ""),
    '06 — From the journal': ("06 — Jurnaldan", "06 — Jurnaldan", "06 — Из журнала", ""),
    'Latest dispatches.': ("So'nggi yozuvlar.", "So'nggi yozuvlar.", "Последние записи.", ""),
    'All entries': ("Hamma yozuvlar", "Barcha yozuvlar", "Все записи", ""),
    'MIN': ("MIN", "MIN", "МИН", ""),
    'WakaTime · this week': ("WakaTime · shu hafta", "WakaTime · shu hafta", "WakaTime · эта неделя", ""),
    'hrs coded': ("soat kod", "soat kod", "часов кода", ""),
    'Download CV': ("CV yuklab oling", "CV yuklab olish", "Скачать CV", ""),

    # Projects
    'All': ("Hammasi", "Barchasi", "Все", ""),
    'Bots': ("Botlar", "Botlar", "Боты", ""),
    'Mobile': ("Mobil", "Mobil", "Мобильные", ""),
    'Work.': ("Ishlar.", "Loyihalar.", "Проекты.", ""),
    'No entries yet': ("Hozircha ishlar yo'q", "Hozircha loyihalar yo'q", "Пока нет проектов", ""),

    # Project detail
    'Back to work': ("Ishlarga qaytish", "Loyihalarga qaytish", "К проектам", ""),
    'Featured': ("Asosiy", "Asosiy", "Главная", ""),
    'Challenge': ("Muammo", "Muammo", "Проблема", ""),
    'Solution': ("Yechim", "Yechim", "Решение", ""),
    'Results': ("Natija", "Natija", "Результат", ""),
    'Stack': ("Stack", "Stack", "Стек", ""),
    'Channels': ("Havolalar", "Havolalar", "Ссылки", ""),
    'Visit live': ("Saytga o'tish", "Saytga o'tish", "Открыть сайт", ""),
    'Next project': ("Keyingi loyiha", "Keyingi loyiha", "Следующий проект", ""),

    # Blog
    'Journal.': ("Jurnal.", "Jurnal.", "Журнал.", ""),
    'Search': ("Qidiruv", "Qidiruv", "Поиск", ""),
    'Search...': ("Qidirish...", "Qidirish...", "Поиск...", ""),
    'Back to journal': ("Jurnalga qaytish", "Jurnalga qaytish", "К журналу", ""),
    'results': ("natija", "natija", "результатов", ""),
    'Nothing found': ("Hech narsa topilmadi", "Hech narsa topilmadi", "Ничего не найдено", ""),
    'No dispatches yet': ("Hozircha yozuvlar yo'q", "Hozircha yozuvlar yo'q", "Пока нет записей", ""),
    'Tags': ("Teglar", "Teglar", "Теги", ""),
    'Share': ("Ulashish", "Ulashish", "Поделиться", ""),
    'Copy link': ("Havolani nusxalash", "Havolani nusxalash", "Скопировать ссылку", ""),
    'Continue reading': ("O'qishni davom eting", "O'qishni davom eting", "Продолжить чтение", ""),
    'Related dispatches.': ("O'xshash yozuvlar.", "O'xshash yozuvlar.", "Похожие записи.", ""),

    # Team
    'y': ("yil", "yil", "лет", ""),
    'Open position': ("Ochiq o'rin", "Ochiq o'rin", "Открытая позиция", ""),
    'Looking for a strong full-stack or bot developer. Introduce yourself.': (
        "Kuchli full-stack yoki bot-developer izlayapmiz. O'zingizni tanitib yozing.",
        "Kuchli full-stack yoki bot-developer izlaymiz. O'zingizni tanitib yozing.",
        "Ищем сильного full-stack или бот-разработчика. Напишите о себе.",
        "",
    ),

    # Contact
    'Contact.': ("Aloqa.", "Aloqa.", "Контакт.", ""),
    "Thanks for your message! We'll be in touch soon.": (
        "Xabaringiz uchun rahmat! Tez orada bog'lanamiz.",
        "Xabaringiz uchun rahmat! Tez orada bog'lanamiz.",
        "Спасибо за сообщение! Скоро свяжемся.",
        "",
    ),
    'Your name': ("Ismingiz", "Ismingiz", "Ваше имя", ""),
    'Email or Telegram': ("Email yoki Telegram", "Email yoki Telegram", "Email или Telegram", ""),
    'About your project': ("Loyihangiz haqida", "Loyihangiz haqida", "О вашем проекте", ""),
    'Send': ("Yuborish", "Yuborish", "Отправить", ""),
    'Or directly': ("Yoki to'g'ridan-to'g'ri", "Yoki to'g'ridan-to'g'ri", "Или напрямую", ""),
    'Message on Telegram': ("Telegram orqali yozish", "Telegram orqali yozish", "Написать в Telegram", ""),
}

LANG_INDEX = {'xo': 0, 'uz': 1, 'ru': 2, 'en': 3}

for lang, idx in LANG_INDEX.items():
    path = f'locale/{lang}/LC_MESSAGES/django.po'
    po = polib.pofile(path)
    touched = 0
    for entry in po:
        if entry.msgid in T:
            value = T[entry.msgid][idx]
            entry.msgstr = value  # '' for en → runtime falls back to msgid
            if 'fuzzy' in entry.flags:
                entry.flags.remove('fuzzy')
            touched += 1
    po.save(path)
    print(f'{lang}: {touched} entries set')
