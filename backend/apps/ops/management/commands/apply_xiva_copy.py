"""Seed SiteSettings with the approved XIVA INK (v4) copy in all 4 languages.

One-shot, explicit command — run once after deploying the v4 redesign:
    venv/bin/python manage.py apply_xiva_copy

Copy source: the v4 design handoff (jaysonkhan-v4/js/i18n.jsx + data.jsx),
approved in the design session on 2026-06-10. Overwrites ONLY the fields
listed below; everything else in SiteSettings is left untouched.
"""
from django.core.management.base import BaseCommand

LANGS = ('xo', 'uz', 'ru', 'en')

# field -> {lang: value}; JSON-list fields hold lists, the rest are strings.
COPY = {
    'hero_eyebrow': {
        'xo': 'VibeCoder · Build Studio · Toshkent',
        'uz': 'VibeCoder · Build Studio · Toshkent',
        'ru': 'VibeCoder · Build Studio · Ташкент',
        'en': 'VibeCoder · Build Studio · Tashkent',
    },
    'hero_title': {
        'xo': "G'oyadan<br>productiongacha,",
        'uz': "G'oyadan<br>productiongacha,",
        'ru': 'От идеи<br>до продакшена,',
        'en': 'From idea<br>to production,',
    },
    'hero_title_em': {
        'xo': "ko'ngil qo'yip.",
        'uz': 'niyat bilan.',
        'ru': 'с намерением.',
        'en': 'with intent.',
    },
    'hero_subtitle': {
        'xo': "Man Jahongir Qo'ziboyev — Xorazmdan chiqqan VibeCoder. Production web ilovalar, Telegram botlar va AI bilan kuchaytirilgan tizimlarni tez quramiz, puxta qilamiz.",
        'uz': "Men Jahongir Qo'ziboyev — Toshkentda build-studio yuritaman. Production web ilovalar, Telegram botlar va AI bilan kuchaytirilgan tizimlarni tez va puxta yetkazib beramiz.",
        'ru': 'Я Джахонгир Кузибоев — веду build-студию в Ташкенте. Production веб-приложения, Telegram-боты и AI-усиленные системы — быстро и надёжно.',
        'en': "I'm Jahongir Kuziboev — running a build studio in Tashkent. We ship production web apps, Telegram bots and AI-augmented systems — fast, and built to last.",
    },
    'availability_badge': {
        'xo': 'Buyurtmaga ochiq',
        'uz': 'Buyurtmaga ochiq',
        'ru': 'Открыт к заказам',
        'en': 'Open for work',
    },
    'hero_location': {
        'xo': 'Toshkent · UZ',
        'uz': 'Toshkent · UZ',
        'ru': 'Ташкент · UZ',
        'en': 'Tashkent · UZ',
    },
    'hero_scroll_label': {
        'xo': 'Pastga sirpaning',
        'uz': 'Pastga aylantiring',
        'ru': 'Листайте вниз',
        'en': 'Scroll down',
    },
    'ticker_items': {
        'xo': ['Web ilovalar · Django', 'Telegram botlar · Aiogram', 'AI-augmented · Claude', 'Mobil meros · Flutter', 'Toshkent · UTC+5'],
        'uz': ['Web ilovalar · Django', 'Telegram botlar · Aiogram', 'AI-augmented · Claude', 'Mobil meros · Flutter', 'Toshkent · UTC+5'],
        'ru': ['Веб-приложения · Django', 'Telegram-боты · Aiogram', 'AI-augmented · Claude', 'Мобильное наследие · Flutter', 'Ташкент · UTC+5'],
        'en': ['Web apps · Django', 'Telegram bots · Aiogram', 'AI-augmented · Claude', 'Mobile legacy · Flutter', 'Tashkent · UTC+5'],
    },
    'manifesto_eyebrow': {
        'xo': '01 — Manifest',
        'uz': '01 — Manifest',
        'ru': '01 — Манифест',
        'en': '01 — Manifesto',
    },
    'manifesto_title': {
        'xo': 'Uch qoida bilan ishlaymiz.',
        'uz': 'Uch tamoyil asosida ishlaymiz.',
        'ru': 'Работаем по трём принципам.',
        'en': 'Three rules we build by.',
    },
    'manifesto_principles': {
        'xo': [
            {'n': '01', 'title': "Tez yetkazamiz, to'g'ri yetkazamiz", 'description': "Haftalar emas, kunlar ichida ishlaydigan natija. Lekin shoshganda ham poydevor mustahkam bo'ladi."},
            {'n': '02', 'title': 'AI quroldir, egasi — odam', 'description': "Claude Code bilan 10x tezlik. Ammo har bir qaror, har bir arxitektura — insonniki. Mas'uliyatni mashinaga ag'darmiymiz."},
            {'n': '03', 'title': 'Uzoqqa chidaydigan qilamiz', 'description': 'Demo uchun emas, real foydalanuvchilar uchun quramiz. Clean architecture, testlar, monitoring — hammasi ichida.'},
        ],
        'uz': [
            {'n': '01', 'title': "Tez yetkazamiz, to'g'ri yetkazamiz", 'description': 'Haftalar emas, kunlar ichida ishlaydigan natija. Tezlik hech qachon poydevor hisobiga bo\'lmaydi.'},
            {'n': '02', 'title': 'AI — qurol, egalik — insonda', 'description': "Claude Code bilan 10x tezlik. Lekin har bir qaror va arxitektura insonniki — mas'uliyat mashinaga o'tkazilmaydi."},
            {'n': '03', 'title': 'Uzoq muddatga quramiz', 'description': 'Demo uchun emas, real foydalanuvchilar uchun. Clean architecture, testlar va monitoring — standart komplekt.'},
        ],
        'ru': [
            {'n': '01', 'title': 'Быстро и правильно', 'description': 'Рабочий результат за дни, а не недели. Но скорость никогда не в ущерб фундаменту.'},
            {'n': '02', 'title': 'AI — инструмент, ответственность — на человеке', 'description': 'Claude Code даёт 10x скорость. Но каждое решение и архитектура — за человеком.'},
            {'n': '03', 'title': 'Строим надолго', 'description': 'Не для демо, а для реальных пользователей. Clean architecture, тесты, мониторинг — в комплекте.'},
        ],
        'en': [
            {'n': '01', 'title': 'Ship fast, ship right', 'description': 'Working software in days, not weeks. But speed never comes at the cost of the foundation.'},
            {'n': '02', 'title': 'AI is the tool, humans own it', 'description': 'Claude Code gives 10x velocity. But every decision and every architecture belongs to a human.'},
            {'n': '03', 'title': 'Built to last', 'description': 'Not for the demo — for real users. Clean architecture, tests and monitoring come standard.'},
        ],
    },
    'metrics_eyebrow': {
        'xo': '02 — Raqamlar',
        'uz': '02 — Raqamlar',
        'ru': '02 — Цифры',
        'en': '02 — Numbers',
    },
    'metrics_title': {
        'xo': 'Gap bilan emas, ish bilan.',
        'uz': "So'z bilan emas, ish bilan.",
        'ru': 'Не словами, а делом.',
        'en': 'Proof, not promises.',
    },
    'metrics_description': {
        'xo': "Mobil davrdan studio davriga — raqamlar o'zi gapiradi.",
        'uz': "Mobil davrdan studio davrigacha — raqamlar o'zi gapiradi.",
        'ru': 'От мобильной эры до студии — цифры говорят сами.',
        'en': 'From the mobile era to the studio era — the numbers speak.',
    },
    'stat_1_label': {'xo': 'Yil tajriba', 'uz': 'Yil tajriba', 'ru': 'Года опыта', 'en': 'Years experience'},
    'stat_2_label': {'xo': 'Yetkazilgan ilova', 'uz': 'Yetkazilgan ilova', 'ru': 'Доставленных приложений', 'en': 'Apps delivered'},
    'stat_3_label': {'xo': 'Yuklab olishlar', 'uz': 'Yuklab olishlar', 'ru': 'Скачиваний', 'en': 'App downloads'},
    'stat_4_label': {'xo': 'Clean Architecture', 'uz': 'Clean Architecture', 'ru': 'Clean Architecture', 'en': 'Clean Architecture'},
    'about_section_eyebrow': {
        'xo': '03 — Kim bu?',
        'uz': '03 — Men haqimda',
        'ru': '03 — Обо мне',
        'en': '03 — About',
    },
    'about_title': {
        'xo': 'Studio · Operator',
        'uz': 'Studio · Operator',
        'ru': 'Студия · Оператор',
        'en': 'Studio · Operator',
    },
    'about_description': {
        'xo': "Full-stack VibeCoder, 3+ yildan beri production tizimlar quraman. Django bilan web, Aiogram bilan botlar, Claude Code bilan tezlik. Ildiz — mobil (Flutter, Android, iOS), endi esa markaz — web + botlar + AI.",
        'uz': "Full-stack VibeCoder, 3+ yildan beri production tizimlar quraman. Django bilan web, Aiogram bilan botlar, Tailwind bilan dizayn tizimlar — barchasi Claude Code va sog'lom workflow bilan kuchaytirilgan. Ildiz — mobil (Flutter, Android, iOS), hozirgi markaz — web + botlar + AI.",
        'ru': 'Full-stack VibeCoder, 3+ года строю production-системы. Веб на Django, боты на Aiogram, дизайн-системы на Tailwind — всё усилено Claude Code. Корни — мобильная разработка (Flutter, Android, iOS), центр тяжести — веб + боты + AI.',
        'en': "Full-stack VibeCoder with 3+ years shipping production systems. Web apps with Django, bots with Aiogram, design systems with Tailwind — all augmented by Claude Code and a sane workflow. Mobile roots (Flutter, Android, iOS); the studio's center of gravity is web + bots + AI.",
    },
    'resume_button_text': {
        'xo': 'CV yuklab oling',
        'uz': 'CV yuklab olish',
        'ru': 'Скачать CV',
        'en': 'Download CV',
    },
    'featured_projects_title': {
        'xo': "So'nggi qurilmalardan bir hovuch.",
        'uz': "So'nggi qurilmalardan namunalar.",
        'ru': 'Несколько недавних сборок.',
        'en': 'A handful of recent builds.',
    },
    'process_eyebrow': {
        'xo': '05 — Jarayon',
        'uz': '05 — Jarayon',
        'ru': '05 — Процесс',
        'en': '05 — Process',
    },
    'process_title': {
        'xo': "Uch bosqich. Ortiqcha gap yo'q.",
        'uz': "Uch bosqich. Ortiqcha byurokratiya yo'q.",
        'ru': 'Три этапа. Без бюрократии.',
        'en': 'Three steps. Zero bureaucracy.',
    },
    'process_steps': {
        'xo': [
            {'n': '01', 'title': 'Kashfiyot', 'description': "Muammoni eshitamiz, scope chizamiz, narx va muddatni ochiq aytamiz. 2-3 kun."},
            {'n': '02', 'title': 'Qurish sprinti', 'description': "Haftasiga demo. Har demo — ishlaydigan, bosib ko'radigan mahsulot. Yashirin ish yo'q."},
            {'n': '03', 'title': 'Launch va parvarish', 'description': "Production'ga chiqaramiz, monitoring o'rnatamiz, o'sishiga qarab turamiz."},
        ],
        'uz': [
            {'n': '01', 'title': 'Kashfiyot', 'description': 'Muammoni tinglaymiz, scope chizamiz, narx va muddatni ochiq kelishamiz. 2-3 kun.'},
            {'n': '02', 'title': 'Qurish sprinti', 'description': "Har hafta demo — ishlaydigan, bosib ko'rsa bo'ladigan mahsulot. Yashirin jarayon yo'q."},
            {'n': '03', 'title': 'Launch va parvarish', 'description': "Production'ga chiqaramiz, monitoring o'rnatamiz, o'sish bilan birga yuramiz."},
        ],
        'ru': [
            {'n': '01', 'title': 'Дискавери', 'description': 'Слушаем проблему, рисуем scope, открыто договариваемся о цене и сроках. 2-3 дня.'},
            {'n': '02', 'title': 'Спринт сборки', 'description': 'Каждую неделю демо — работающий, кликабельный продукт. Никаких скрытых процессов.'},
            {'n': '03', 'title': 'Запуск и забота', 'description': 'Выводим в production, ставим мониторинг, растём вместе.'},
        ],
        'en': [
            {'n': '01', 'title': 'Discovery', 'description': 'We hear the problem, draw the scope, agree price and timeline in the open. 2-3 days.'},
            {'n': '02', 'title': 'Build sprint', 'description': 'A demo every week — working, clickable product. No hidden process.'},
            {'n': '03', 'title': 'Launch & care', 'description': 'We ship to production, wire up monitoring, and grow with you.'},
        ],
    },
    'cta_eyebrow': {
        'xo': 'Gaplashamizmi?',
        'uz': 'Gaplashamizmi?',
        'ru': 'Поговорим?',
        'en': 'Shall we talk?',
    },
    'cta_title_pre': {
        'xo': 'Keling, birga',
        'uz': 'Keling, birgalikda',
        'ru': 'Давайте построим',
        'en': "Let's build it",
    },
    'cta_title_em': {
        'xo': 'quramiz.',
        'uz': 'quramiz.',
        'ru': 'вместе.',
        'en': 'together.',
    },
    'cta_description': {
        'xo': "Web ilova, Telegram bot yo AI tizimmi — gal, gaplashamiz. Q2 2026 uchun ikkita o'rin ochilyapti.",
        'uz': 'Web ilova, Telegram bot yoki AI tizim kerakmi? Q2 2026 uchun ikkita o\'rin ochilmoqda.',
        'ru': 'Веб-приложение, Telegram-бот или AI-система? На Q2 2026 открываются два слота.',
        'en': 'A web app, a Telegram bot, or an AI-augmented system? Two slots opening for Q2 2026.',
    },
    'cta_button_text': {
        'xo': 'Loyiha boshlash',
        'uz': 'Loyiha boshlash',
        'ru': 'Начать проект',
        'en': 'Start a project',
    },
    'cta_response_label': {
        'xo': '24 SOAT ICHIDA JAVOB',
        'uz': '24 SOAT ICHIDA JAVOB',
        'ru': 'ОТВЕТ В ТЕЧЕНИЕ 24 ЧАСОВ',
        'en': 'REPLY WITHIN 24 HOURS',
    },
    'nav_cta_text': {
        'xo': 'Gal, ishlashamiz',
        'uz': 'Hamkorlik',
        'ru': 'Сотрудничество',
        'en': 'Hire the studio',
    },
    'footer_description': {
        'xo': 'VibeCoder — AI bilan kuchaytirilgan dasturlash orqali production web ilovalar va Telegram botlar.',
        'uz': 'VibeCoder — AI bilan kuchaytirilgan dasturlash orqali production web ilovalar va Telegram botlar.',
        'ru': 'VibeCoder — production веб-приложения и Telegram-боты через AI-усиленную разработку.',
        'en': 'VibeCoder — shipping production web apps & Telegram bots via AI-augmented development.',
    },
    'footer_text': {
        'xo': '© 2026 JAYSONKHAN · Barcha huquqlar himoyalangan.',
        'uz': '© 2026 JAYSONKHAN · Barcha huquqlar himoyalangan.',
        'ru': '© 2026 JAYSONKHAN · Все права защищены.',
        'en': '© 2026 JAYSONKHAN · All rights reserved.',
    },
    'projects_page_title': {
        'xo': 'Ishlar.',
        'uz': 'Loyihalar.',
        'ru': 'Проекты.',
        'en': 'Work.',
    },
    'projects_page_subtitle': {
        'xo': "Web ilovalar, Telegram botlar va mobil meros — hammasi production'da.",
        'uz': "Web ilovalar, Telegram botlar va mobil meros — barchasi production'da.",
        'ru': 'Веб-приложения, Telegram-боты и мобильное наследие — всё в production.',
        'en': 'Web apps, Telegram bots, and the mobile legacy — all in production.',
    },
    'blog_page_title': {
        'xo': 'Jurnal.',
        'uz': 'Jurnal.',
        'ru': 'Журнал.',
        'en': 'Journal.',
    },
    'blog_page_subtitle': {
        'xo': 'Qurish jarayonidan yozuvlar — Django, botlar, AI workflow.',
        'uz': 'Qurish jarayonidan yozuvlar — Django, botlar, AI workflow.',
        'ru': 'Записи из процесса — Django, боты, AI workflow.',
        'en': 'Dispatches from the build process — Django, bots, AI workflow.',
    },
    'contact_page_title': {
        'xo': 'Aloqa.',
        'uz': 'Aloqa.',
        'ru': 'Контакт.',
        'en': 'Contact.',
    },
    'contact_page_subtitle': {
        'xo': 'Yozing — 24 soat ichida javob beramiz. Telegram tezroq ishlaydi.',
        'uz': 'Yozing — 24 soat ichida javob beramiz. Telegram orqali tezroq.',
        'ru': 'Напишите — ответим в течение 24 часов. Telegram быстрее.',
        'en': 'Write to us — we reply within 24 hours. Telegram is faster.',
    },
    'team_hero_headline': {
        'xo': 'Jamoa.',
        'uz': 'Jamoa.',
        'ru': 'Команда.',
        'en': 'Team.',
    },
    'team_intro': {
        'xo': "Kichik studio — full-stack quruvchilar. Muammoga qaysi qurol mos bo'lsa, o'shani ishlatamiz.",
        'uz': 'Kichik studio — full-stack quruvchilar, dizaynerlar, operatorlar. Muammoga mos qurolni tanlaymiz.',
        'ru': 'Небольшая студия — full-stack строители, дизайнеры, операторы.',
        'en': 'A small studio of full-stack builders, designers and operators.',
    },
}

# Language-neutral fields (single column, no modeltranslation)
PLAIN = {
    'hero_section_count': '01 / 07',
    'stat_1_count': 3, 'stat_1_suffix': '+',
    'stat_2_count': 30, 'stat_2_suffix': '+',
    'stat_3_count': 1, 'stat_3_suffix': 'M+',
    'stat_4_count': 100, 'stat_4_suffix': '%',
}


class Command(BaseCommand):
    help = 'Apply the approved XIVA INK v4 copy to SiteSettings (all 4 languages)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='List the fields that would change without saving',
        )

    def handle(self, *args, **options):
        from core.models import SiteSettings

        obj = SiteSettings.load()
        changed = []

        for field, values in COPY.items():
            for lang in LANGS:
                col = f'{field}_{lang}'
                if not hasattr(obj, col):
                    # Field isn't registered for translation — write the base column once (xo pass)
                    if lang == 'xo' and hasattr(obj, field):
                        setattr(obj, field, values[lang])
                        changed.append(field)
                    continue
                setattr(obj, col, values[lang])
                changed.append(col)

        for field, value in PLAIN.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
                changed.append(field)

        if options['dry_run']:
            self.stdout.write('Would update %d columns:' % len(changed))
            for col in changed:
                self.stdout.write(f'  · {col}')
            return

        obj.save()
        self.stdout.write(self.style.SUCCESS(
            f'XIVA INK v4 copy applied — {len(changed)} columns updated on SiteSettings.'
        ))
