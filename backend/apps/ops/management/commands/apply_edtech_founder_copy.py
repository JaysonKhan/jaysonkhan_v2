"""Apply jaysonkhan.com AI EdTech founder positioning.

Idempotent production command (deploy.sh runs it on EVERY deploy — these fields
are code-owned; admin hand-edits to them are overwritten). Keeps `xo` as the
default Khorezm dialect locale (owner's signature voice — man/mani, -la plural,
gal/girish), updates the SiteSettings singleton in all four locales
(xo, uz, ru, en), refreshes the Experience timeline wording from the 2026-07
resume, and rewrites any legacy "VibeCoder" Experience-timeline title.

Facts source (2026-07): resume + UzExam PTA-2026 docs — 3+ yrs experience,
Career facts: 25+ apps shipped (UIC 20+, freelance 5+). Product facts refreshed
2026-09-21; see docs/project-facts-2026-09.md for counts and definitions.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

LANGS = ("xo", "uz", "ru", "en")

COPY = {
    # The legal name belongs in the <title>: name searches ("Jahongir
    # Qo'ziboyev", "Жахонгир Кузибоев") were finding unrelated people because
    # the string appeared nowhere except JSON-LD and meta keywords. The brand
    # name stays first — it's how he's actually known online.
    "site_title": {
        "xo": "Jayson Khan (Jahongir Qo'ziboyev) — AI va mobil dasturchi | UzExam asoschisi",
        "uz": "Jayson Khan (Jahongir Qo'ziboyev) — AI va mobil dasturchi | UzExam asoschisi",
        "ru": "Jayson Khan (Жахонгир Кузибоев) — AI и мобильный разработчик | Основатель UzExam",
        "en": "Jayson Khan (Jahongir Qo'ziboyev) — AI & Mobile Developer | Founder of UzExam",
    },
    "site_tagline": {
        "xo": "AI yordamida EdTech mahsulotla, test platformala va ta'lim analitikasini quramiz.",
        "uz": "AI yordamida EdTech mahsulotlar, test platformalari va ta'lim analitikasini quramiz.",
        "ru": "AI-продукты для EdTech: тестовые платформы, образовательная аналитика и автоматизация.",
        "en": "AI-powered EdTech products, testing platforms and education analytics for Uzbekistan.",
    },
    # NOTE: meta_description is max_length=160 — keep every locale under it or
    # the seeder raises on save. Legal name + role terms come first.
    "meta_description": {
        "xo": "Jayson Khan (Jahongir Qo'ziboyev) — O'zbekistonda AI, mobil va full-stack dasturchi, UzExam va "
              "EduStats asoschisi. 25+ ilova, 85k+ savol.",
        "uz": "Jayson Khan (Jahongir Qo'ziboyev) — O'zbekistonda AI, mobil va full-stack dasturchi, UzExam va "
              "EduStats asoschisi. 25+ ilova, 85k+ savol.",
        "ru": "Jayson Khan (Жахонгир Кузибоев) — AI, мобильный и full-stack разработчик из Узбекистана, основатель UzExam и EduStats. 25+ приложений.",
        "en": "Jayson Khan (Jahongir Qo'ziboyev) — AI, mobile and full-stack developer in Uzbekistan, founder "
              "of UzExam and EduStats. 25+ apps, 85k+ questions.",
    },
    # max_length=255 — Google ignores this tag entirely, Yandex weighs it
    # lightly, so spend the budget on the name variants and role terms that
    # actually differ per script instead of restating the product story.
    "meta_keywords": {
        "xo": "Jahongir Qo'ziboyev, Qo'ziboyev Jahongir, Jayson Khan, JaysonKhan, AI dasturchi, mobil dasturchi, full stack dasturchi, Flutter dasturchi, O'zbekiston dasturchi, UzExam asoschisi, EduStats, AI EdTech, sun'iy intellekt",
        "uz": "Jahongir Qo'ziboyev, Qo'ziboyev Jahongir, Jayson Khan, JaysonKhan, AI dasturchi, mobil dasturchi, full stack dasturchi, Flutter dasturchi, O'zbekiston dasturchi, UzExam asoschisi, EduStats, AI EdTech, sun'iy intellekt",
        "ru": "Жахонгир Кузибоев, Кузибоев Жахонгир, Jayson Khan, JaysonKhan, AI разработчик, мобильный разработчик, full stack разработчик, Flutter разработчик, разработчик Узбекистан, основатель UzExam, EduStats, AI EdTech",
        "en": "Jahongir Qo'ziboyev, Qoziboyev Jahongir, Jayson Khan, JaysonKhan, AI developer, mobile developer, full stack developer, Flutter developer, Uzbekistan developer, UzExam founder, EduStats, AI EdTech",
    },
    "hero_eyebrow": {
        "xo": "AI · Mobil · Full-stack dasturchi · UzExam · EduStats · O'zbekiston",
        "uz": "AI · Mobil · Full-stack dasturchi · UzExam · EduStats · O'zbekiston",
        "ru": "AI · Mobile · Full-stack разработчик · UzExam · EduStats · Узбекистан",
        "en": "AI · Mobile · Full-stack developer · UzExam · EduStats · Uzbekistan",
    },
    "hero_title": {
        "xo": "O'zbekistonda AI asosidagi<br>EdTech mahsulotla",
        "uz": "O'zbekistonda AI asosidagi<br>EdTech mahsulotlar",
        "ru": "AI-продукты для<br>EdTech в Узбекистане",
        "en": "AI-powered EdTech<br>products for Uzbekistan",
    },
    "hero_title_em": {
        "xo": "quraman.",
        "uz": "quraman.",
        "ru": "строю.",
        "en": "built to win.",
    },
    "hero_subtitle": {
        "xo": "Man Jayson Khan (Jahongir Qo'ziboyev) — AI, mobil va full-stack dasturchi, UzExam va EduStats "
              "asoschisiman. Bitta odam + 24/7 AI-agentla bilan test platformala, AI mentorla va ta'lim "
              "analitikasi quraman. 85k+ ochiq savol va 21k+ ro'yxatdan o'tgan foydalanuvchi — UzExam'da.",
        "uz": ('Consort Group’da Mobile Developer sifatida Growz va Bizon ilovalariga AI va xarita funksiyalarini '
               'qo‘shish ustida ishlayman. UzExam asoschisiman: yettita Flutter ilovasi va Django platformasini '
               'rivojlantiraman. EduStats ham o‘z loyiham.'),
        "ru": ('Mobile Developer в Consort Group: работаю над AI-интеграциями и картами в Growz и Bizon. Основал '
               'UzExam, где развиваю семь Flutter-приложений и платформу на Django. Также создал EduStats.'),
        "en": ('Mobile Developer at Consort Group, working on AI integrations and maps in Growz and Bizon. I '
               'founded UzExam, where I develop seven Flutter apps and the Django platform, and created EduStats.'),
    },
    "availability_badge": {
        "xo": "AI EdTech hamkorlikka ochiq",
        "uz": "AI EdTech hamkorlikka ochiq",
        "ru": "Открыт к AI EdTech партнёрствам",
        "en": "Open to AI EdTech partnerships",
    },
    "about_title": {
        "xo": "AI EdTech Founder",
        "uz": 'Mobil ilovalar va o‘z mahsulotlarim.',
        "ru": 'Мобильные приложения и собственные продукты.',
        "en": 'Mobile engineering and products of my own.',
    },
    "about_description": {
        "xo": "Man Jayson Khan (Jahongir Qo'ziboyev) — Xorazmdan chiqqan AI, mobil va full-stack dasturchi, AI "
              "EdTech founder. Mobil davrda 3+ yilda 25+ ilova yetkazganman (UIC Group'da korporativ ilovala, "
              "TaxPay fintech). Endi studio davri: kod, QA, monitoring va incident-response — 24/7 "
              "AI-agentlada; strategiya, kontent sifati va mas'uliyat — manda. Natija: 3 oyda yolg'iz qurilgan "
              "UzExam (85k+ ochiq savol, 7 mobil ilova) va 53k+ Telegram auditoriyali EduStats. President Tech "
              "Award 2026 ishtirokchisiman.",
        "uz": ('Consort Group’da Mobile Developer sifatida Growz va Bizon ilovalariga AI va xarita funksiyalarini '
               'qo‘shish ustida ishlayman. UzExam asoschisiman: yettita Flutter ilovasi va Django platformasini '
               'rivojlantiraman. EduStats ham o‘z loyiham.'),
        "ru": ('Mobile Developer в Consort Group: работаю над AI-интеграциями и картами в Growz и Bizon. Основал '
               'UzExam, где развиваю семь Flutter-приложений и платформу на Django. Также создал EduStats.'),
        "en": ('Mobile Developer at Consort Group, working on AI integrations and maps in Growz and Bizon. I '
               'founded UzExam, where I develop seven Flutter apps and the Django platform, and created EduStats.'),
    },
    # ── Stats bar: labels MUST travel with the counts (the 2026-06 deploy
    #    updated counts only and left mobile-era labels → "40k+ Years experience").
    "stat_1_label": {
        "xo": "Yil tajriba",
        "uz": "Yil tajriba",
        "ru": "Года опыта",
        "en": "Years experience",
    },
    "stat_2_label": {
        "xo": "Yetkazilgan ilovala",
        "uz": "Yetkazilgan ilovalar",
        "ru": "Выпущенных приложений",
        "en": "Apps delivered",
    },
    "stat_3_label": {
        "xo": "Ochiq savolla (UzExam)",
        "uz": "Ochiq savollar (UzExam)",
        "ru": "Опубликованных вопросов (UzExam)",
        "en": "Published questions (UzExam)",
    },
    "stat_4_label": {
        "xo": "Ro'yxatdan o'tganla (UzExam)",
        "uz": "Ro'yxatdan o'tganlar (UzExam)",
        "ru": "Зарегистрированных пользователей (UzExam)",
        "en": "Registered users (UzExam)",
    },
    "featured_projects_title": {
        "xo": "AI EdTech ekotizimidagi asosiy mahsulotla.",
        "uz": "AI EdTech ekotizimidagi asosiy mahsulotlar.",
        "ru": "Ключевые продукты AI EdTech экосистемы.",
        "en": "Core products in the AI EdTech ecosystem.",
    },
    "projects_page_title": {
        "xo": "AI EdTech va savdo loyihala.",
        "uz": "Yaratilgan mahsulotlar.",
        "ru": "Созданные продукты.",
        "en": "Products in the real world.",
    },
    "projects_page_subtitle": {
        "xo": "UzExam, EduStats, Vaygo, AI mentorla, test platformala va ta'lim analitikasi va savdo "
              "bo'yicha mahsulotla.",
        "uz": "UzExam, EduStats va Vaygo — ta'lim, analitika va savdo uchun web, Telegram va mobil mahsulotlar.",
        "ru": "UzExam, EduStats и Vaygo — веб, Telegram и мобильные продукты для образования, аналитики и "
              "торговли.",
        "en": "UzExam, EduStats and Vaygo — web, Telegram and mobile products for education, analytics and "
              "commerce.",
    },
    "blog_page_title": {
        "xo": "AI EdTech jurnal.",
        "uz": "AI EdTech jurnal.",
        "ru": "AI EdTech журнал.",
        "en": "AI EdTech Journal.",
    },
    "blog_page_subtitle": {
        "xo": "AI, EdTech, test platformala, product building va O'zbekistonda ta'lim mahsulotlari haqida yozuvla.",
        "uz": "AI, EdTech, test platformalari, product building va O'zbekistonda ta'lim mahsulotlari haqida yozuvlar.",
        "ru": "Заметки про AI, EdTech, тестовые платформы, product building и образовательные продукты в Узбекистане.",
        "en": "Notes on AI, EdTech, testing platforms, product building and education products in Uzbekistan.",
    },
    "contact_page_title": {
        "xo": "AI EdTech hamkorlik.",
        "uz": "AI EdTech hamkorlik.",
        "ru": "AI EdTech сотрудничество.",
        "en": "AI EdTech Collaboration.",
    },
    "contact_page_subtitle": {
        "xo": "Test platforma, AI mentor, ta'lim analitikasi yo EdTech growth bo'yicha yozavering — Telegram eng tez kanal.",
        "uz": "Test platforma, AI mentor, ta'lim analitikasi yoki EdTech growth bo'yicha yozing — Telegram eng tez kanal.",
        "ru": "Напишите про тестовую платформу, AI mentor, образовательную аналитику или EdTech growth — Telegram самый быстрый канал.",
        "en": "Write about a testing platform, AI mentor, education analytics or EdTech growth — Telegram is the fastest channel.",
    },
    "nav_cta_text": {
        "xo": "Hamkorlik",
        "uz": "Hamkorlik",
        "ru": "Сотрудничество",
        "en": "Collaborate",
    },
    "footer_description": {
        "xo": "Jayson Khan — UzExam va EduStats asoschisi. AI yordamida EdTech, test platformala va ta'lim analitikasi quradi.",
        "uz": "Jayson Khan — UzExam va EduStats asoschisi. AI yordamida EdTech, test platformalari va ta'lim analitikasi quradi.",
        "ru": "Jayson Khan — основатель UzExam и EduStats. AI-продукты для EdTech, тестов и образовательной аналитики.",
        "en": "Jayson Khan — founder of UzExam and EduStats. Building AI-powered EdTech, testing platforms and education analytics.",
    },
    # ── CTA + contact availability: were seeded once with "Q2 2026" and went
    #    stale — owned here now, phrased timeless on purpose.
    "cta_description": {
        "xo": "AI EdTech loyiha, test platforma yo hamkorlik taklifimi — gal, gaplashamiz. Brifni tashlang, qolganini o'zim surishtiraman.",
        "uz": "AI EdTech loyiha, test platforma yoki hamkorlik taklifimi — keling, gaplashamiz. Brifni tashlang, qolganini o'zim surishtiraman.",
        "ru": "AI EdTech проект, тестовая платформа или предложение о партнёрстве — давайте обсудим. Пришлите бриф, остальное я уточню сам.",
        "en": "An AI EdTech project, a testing platform or a partnership? Bring the brief — I'll take it from there.",
    },
    "contact_availability_status": {
        "xo": "Hamkorlikka ochiq",
        "uz": "Hamkorlikka ochiq",
        "ru": "Открыт к сотрудничеству",
        "en": "Open to partnerships",
    },
    "contact_availability_note": {
        "xo": "AI EdTech hamkorlik va tanlangan loyihala uchun ochiq. Toshkent, UTC+5.",
        "uz": "AI EdTech hamkorlik va tanlangan loyihalar uchun ochiq. Toshkent, UTC+5.",
        "ru": "Открыт для AI EdTech партнёрств и отдельных проектов. Ташкент, UTC+5.",
        "en": "Open for AI EdTech partnerships and selected briefs. Tashkent, UTC+5.",
    },
    "faq_title": {
        "xo": "Ko'p so'raladigan savolla",
        "uz": "Ko'p so'raladigan savollar",
        "ru": "Часто задаваемые вопросы",
        "en": "Frequently asked questions",
    },
    "faq_items": {
        "xo": [
            {"q": "Jahongir Qo'ziboyev kim?", "a": "Jahongir Qo'ziboyev (internetda Jayson Khan) — O'zbekistonda ishlaydigan AI, mobil va full-stack dasturchi, UzExam va EduStats asoschisi. Kirilda Жаҳонгир Қўзибоев, ruschada Жахонгир Кузибоев deb yoziladi."},
            {"q": "Jayson Khan kim?", "a": "Jayson Khan (Jahongir Qo'ziboyev) — O'zbekistonda AI EdTech mutaxassisi, UzExam va EduStats asoschisi. Test platformala, ta'lim analitikasi va AI mentor tizimlarini quradi. President Tech Award 2026 ishtirokchisi."},
            {"q": "UzExam nima?", "a": "UzExam (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon"
                                       " platformasi: 85k+ ochiq savol, imtihon yo‘nalishla (DTM, IELTS, "
                                       "SAT, Avtotest va boshqala), takrorlanmas savolla (Uniqueness "
                                       "Engine), SM-2 va antifraud reyting. Telegram bilan chambarchas "
                                       "ishlaydi."},
            {"q": "EduStats nima?", "a": "EduStats (edustats.uz) — talabalar fikri va ta'lim analitikasi "
                                         "platformasi: universitetla reytingi, 53k+ Telegram "
                                         "foydalanuvchili auditoriyasi va 121 OTM o'tish ballari "
                                         "(2020–2025)."},
            {"q": "Bitta odam bularni qale eplaydi?", "a": "Arxitektura shunaqa: kod yozish, UI, QA, monitoring va tungi incident-response — 24/7 AI-agentlada. Strategiya, kontent sifati, mijozla va mas'uliyat — founderda. Shu tandem 3 oyda 54 modulli jonli platformani yolg'iz qurishga imkon berdi."},
            {"q": "Jayson Khan nimaga ixtisoslashgan?", "a": "Ta'limda AI, adaptiv test va imtihon platformala, ta'lim analitikasi, o'quvchi progressi, AI mentorla va mahsulot strategiyasi."},
            {"q": "Jayson Khan bilan qale bog'lansa bo'ladi?", "a": "jaysonkhan.com saytidagi kontakt sahifasi yo Telegram (@jaysonkhan) orqali — Telegram eng tez javob beradigan kanal."},
        ],
        "uz": [
            {"q": "Jahongir Qo'ziboyev kim?", "a": "Jahongir Qo'ziboyev (internetda Jayson Khan) — O'zbekistonda ishlaydigan AI, mobil va full-stack dasturchi, UzExam va EduStats asoschisi. Kirilda Жаҳонгир Қўзибоев, ruschada Жахонгир Кузибоев deb yoziladi."},
            {"q": "Jayson Khan kim?", "a": "Jayson Khan (Jahongir Qo'ziboyev) — O'zbekistonda AI EdTech mutaxassisi, UzExam va EduStats asoschisi. Test platformalari, ta'lim analitikasi va AI mentor tizimlarini quradi. President Tech Award 2026 ishtirokchisi."},
            {"q": "UzExam nima?", "a": "UzExam — 85k+ ochiq savol, 21k+ ro'yxatdan o'tgan foydalanuvchi va 7 "
                                       "mobil ilova. IELTS, Multilevel, SAT, DTM, Milliy sertifikat, Avtotest "
                                       "va Intervyu — web, Telegram va Flutter'da."},
            {"q": "EduStats nima?", "a": "EduStats — 53k+ Telegram foydalanuvchi, katalogda 193 faol OTM va 121"
                                         " OTM bo'yicha o'tish ballari. Talabalar fikri, reytinglar va manbali "
                                         "ta'lim statistikasi bir joyda."},
            {"q": "Bir odam bularning hammasini qanday uddalaydi?", "a": "Arxitektura shunday qurilgan: kod yozish, UI, QA, monitoring va tungi incident-response — 24/7 AI-agentlarda. Strategiya, kontent sifati, mijozlar va mas'uliyat — founderda. Shu tandem 3 oyda 54 modulli jonli platformani yolg'iz qurishga imkon berdi."},
            {"q": "Jayson Khan nimaga ixtisoslashgan?", "a": "Ta'limda AI, adaptiv test va imtihon platformalari, ta'lim analitikasi, o'quvchi progressi, AI mentorlar va mahsulot strategiyasi."},
            {"q": "Jayson Khan bilan qanday bog'lanish mumkin?", "a": "jaysonkhan.com saytidagi kontakt sahifasi yoki Telegram (@jaysonkhan) orqali — Telegram eng tez javob beradigan kanal."},
        ],
        "ru": [
            {"q": "Кто такой Жахонгир Кузибоев?", "a": "Жахонгир Кузибоев (в интернете — Jayson Khan) — AI, мобильный и full-stack разработчик из Узбекистана, основатель UzExam и EduStats. По-узбекски Jahongir Qo'ziboyev, узбекской кириллицей Жаҳонгир Қўзибоев."},
            {"q": "Кто такой Jayson Khan?", "a": "Jayson Khan (Жахонгир Кузибоев) — AI EdTech специалист, основатель UzExam и EduStats из Ташкента, Узбекистан. Строит тестовые платформы, образовательную аналитику и системы AI-менторов. Участник President Tech Award 2026."},
            {"q": "Что такое UzExam?", "a": "UzExam — 85k+ опубликованных вопросов, 21k+ "
                                                    "зарегистрированных пользователей и 7 мобильных приложений: "
                                                    "IELTS, Multilevel, SAT, DTM, национальный сертификат, "
                                                    "автотест и интервью."},
            {"q": "Что такое EduStats?", "a": "EduStats — 53k+ пользователей Telegram, 193 активных вуза в "
                                                      "каталоге и проходные баллы для 121 вуза. Отзывы студентов, "
                                                      "рейтинги и статистика образования с указанием источников."},
            {"q": "Как один человек справляется со всем этим?", "a": "Так устроена архитектура: код, UI, QA, мониторинг и ночной incident-response — на AI-агентах 24/7. Стратегия, качество контента, клиенты и ответственность — на основателе. Этот тандем позволил в одиночку построить живую платформу из 54 модулей за 3 месяца."},
            {"q": "На чём специализируется Jayson Khan?", "a": "AI в образовании, адаптивные тестовые и экзаменационные платформы, образовательная аналитика, прогресс студентов, AI-менторы и продуктовая стратегия."},
            {"q": "Как связаться с Jayson Khan?", "a": "Через страницу контактов на jaysonkhan.com или в Telegram (@jaysonkhan) — Telegram отвечает быстрее всего."},
        ],
        "en": [
            {"q": "Who is Jahongir Qo'ziboyev?", "a": "Jahongir Qo'ziboyev (known online as Jayson Khan) is an AI, mobile and full-stack developer based in Uzbekistan and the founder of UzExam and EduStats. Also spelled Жаҳонгир Қўзибоев (Uzbek Cyrillic) and Жахонгир Кузибоев (Russian)."},
            {"q": "Who is Jayson Khan?", "a": "Jayson Khan (Jahongir Qo'ziboyev) is an AI EdTech specialist and founder of UzExam and EduStats, based in Tashkent, Uzbekistan. He builds testing platforms, education analytics and AI mentor systems. President Tech Award 2026 participant."},
            {"q": "What is UzExam?", "a": "UzExam — 85k+ published questions, 21k+ registered users and 7 "
                                          "mobile apps: IELTS, Multilevel, SAT, DTM, national certification, "
                                          "driving tests and interviews."},
            {"q": "What is EduStats?", "a": "EduStats — 53k+ Telegram users, 193 active university listings and"
                                            " admission scores for 121 universities. Student reviews, rankings "
                                            "and source-backed education statistics."},
            {"q": "How does one person run all of this?", "a": "By architecture: coding, UI, QA, monitoring and 3 AM incident response run on AI agents 24/7. Strategy, content quality, customers and accountability stay with the founder. That tandem shipped a live 54-module platform solo in 3 months."},
            {"q": "What does Jayson Khan specialize in?", "a": "AI in education, adaptive testing and exam platforms, education analytics, student progress tracking, AI mentors and product strategy."},
            {"q": "How can I contact Jayson Khan?", "a": "Through the contact page on jaysonkhan.com or via Telegram (@jaysonkhan) — Telegram is the fastest channel."},
        ],
    },
}

PLAIN = {
    "site_author": "Jayson Khan",
    "site_author_initials": "JK",
    "logo_text": "Jayson Khan",
    "og_url": "https://jaysonkhan.com",
    "nav_cta_url": "/contact/",
    "hero_location": "Tashkent · Uzbekistan",
    # Stats bar counts — keep in sync with the stat_N_label entries in COPY:
    # 3+ years · 25+ apps · 85k+ published questions · 21k+ UzExam registered users
    "stat_1_count": 3,
    "stat_1_suffix": "+",
    "stat_2_count": 25,
    "stat_2_suffix": "+",
    "stat_3_count": 85,
    "stat_3_suffix": "k+",
    "stat_4_count": 21,
    "stat_4_suffix": "k+",
}

# Experience timeline wording from the confirmed 2026-09 resume. Rows are matched by
# `company__icontains` and NEVER created here (rows/dates stay admin-owned) —
# only position/description wording is code-owned.
EXPERIENCE = [{'match': 'Consort',
               'position': {'xo': 'Mobile Developer',
                            'uz': 'Mobile Developer',
                            'ru': 'Mobile Developer',
                            'en': 'Mobile Developer'},
               'description': {'xo': 'Growz va Bizon ilovalari ustida ishlayman. Hozir ikkala mobil mahsulotga AI '
                                     'integratsiya qilish va xarita funksiyalarini ishlab chiqish bilan '
                                     'shug‘ullanaman.',
                               'uz': 'Growz va Bizon ilovalari ustida ishlayman. Hozir ikkala mobil mahsulotga AI '
                                     'integratsiya qilish va xarita funksiyalarini ishlab chiqish bilan '
                                     'shug‘ullanaman.',
                               'ru': 'Работаю над приложениями Growz и Bizon. Сейчас занимаюсь интеграцией AI в '
                                     'оба мобильных продукта и разработкой функций карты.',
                               'en': 'Develop Flutter features for Growz and Bizon. Current work focuses on '
                                     'integrating AI into both mobile products and building and improving map '
                                     'features.'}},
              {'match': 'UzExam',
               'position': {'xo': 'Founder & AI EdTech Specialist',
                            'uz': 'Asoschi va Mobile / Full-Stack Developer',
                            'ru': 'Основатель и Mobile / Full-Stack Developer',
                            'en': 'Founder & Mobile / Full-Stack Developer'},
               'description': {'xo': "85k+ ochiq savol, 21k+ ro'yxatdan o'tgan foydalanuvchi va 7 mobil ilova. "
                                     'IELTS, Multilevel, SAT, DTM, Milliy sertifikat, Avtotest va Intervyu — web, '
                                     "Telegram va Flutter'da.",
                               'uz': 'UzExam asoschisi sifatida IELTS, Multilevel, SAT, DTM, Milliy sertifikat, '
                                     'Avtotest va Intervyu uchun yettita Flutter ilovasini ishlab chiqaman. '
                                     'Umumiy mobil arxitektura, autentifikatsiya, mashqlar, obuna va Django '
                                     'backendini yuritaman. EduStats ta’lim platformasini ham yaratganman.',
                               'ru': 'Основал UzExam и разрабатываю семь Flutter-приложений: IELTS, Multilevel, '
                                     'SAT, DTM, Milliy sertifikat, Avtotest и Intervyu. Поддерживаю общую '
                                     'мобильную архитектуру, авторизацию, тренировочные задания, подписки и '
                                     'Django-бэкенд. Также создал образовательную платформу EduStats.',
                               'en': 'Founded UzExam and develop seven Flutter apps: IELTS, Multilevel, SAT, DTM, '
                                     'Milliy sertifikat, Avtotest and Intervyu. Maintain shared mobile '
                                     'architecture, authentication, practice flows, subscriptions and the Django '
                                     'backend. Also created the EduStats education platform.'}},
              {'match': 'Soliq',
               'position': {'xo': 'Software Engineer — Flutter / Fintech',
                            'uz': 'Flutter Developer · TaxPay',
                            'ru': 'Flutter Developer · TaxPay',
                            'en': 'Flutter Developer · TaxPay'},
               'description': {'xo': "TaxPay fintech to'lov ilovasini noldan qurdim: Flutter + Clean "
                                     'Architecture, karta ulash, OTP, tranzaksiyala va PCI talablariga mos REST '
                                     'integratsiyala. Ilova production-ready darajaga yetkazildi.',
                               'uz': 'TaxPay to‘lov ilovasini Flutter, Clean Architecture va BLoC asosida qurdim. '
                                     'Karta ulash, OTP, to‘lovlar va tranzaksiyalar tarixini ishlab chiqdim. '
                                     'Ilova ishga tushirishga tayyor holatga yetkazildi, ammo bo‘lim yopilgach '
                                     'ommaga chiqarilmadi.',
                               'ru': 'Разработал TaxPay на Flutter с Clean Architecture и BLoC: привязка карт, '
                                     'OTP, платежи и история транзакций. Приложение было готово к запуску, но '
                                     'после закрытия отдела не вышло в публичный доступ.',
                               'en': 'Built TaxPay with Flutter, Clean Architecture and BLoC: card binding, OTP '
                                     'verification, payments and transaction history. Delivered the app to a '
                                     'production-ready stage; it was not publicly released after the department '
                                     'closed.'}},
              {'match': 'AIBA',
               'position': {'xo': 'Mobile Team Lead — AI Business Assistant',
                            'uz': 'Mobile Team Lead · AI Business Assistant',
                            'ru': 'Mobile Team Lead · AI Business Assistant',
                            'en': 'Mobile Team Lead · AI Business Assistant'},
               'description': {'xo': 'AIBA loyihasida mobil jamoaga yetakchilik qildim: AI vositala, generativ '
                                     "servisla va aqlli assistent funksiyalarini mobil ilovalarga qo'shdik; code "
                                     'review va mentorlik manda edi.',
                               'uz': 'AI assistent funksiyalari, autentifikatsiya, push-bildirishnomalar, SQLite '
                                     'orqali oflayn saqlash va ko‘p tilli interfeys ustida ishladim. Mobil jamoa '
                                     'vazifalarini muvofiqlashtirdim, kodni ko‘rib chiqish va dasturchilarga '
                                     'yordam berishda qatnashdim.',
                               'ru': 'Работал над функциями AI-ассистента, авторизацией, push-уведомлениями, '
                                     'офлайн-хранилищем SQLite и многоязычным интерфейсом. Координировал задачи '
                                     'мобильной команды, участвовал в ревью кода и помогал разработчикам.',
                               'en': 'Worked on AI assistant features, authentication, push notifications, SQLite '
                                     'offline storage and multilingual interfaces. Coordinated mobile tasks, '
                                     'reviewed code and supported other developers.'}},
              {'match': 'UIC',
               'position': {'xo': 'Flutter Mobile Engineer',
                            'uz': 'Flutter Developer',
                            'ru': 'Flutter Developer',
                            'en': 'Flutter Developer'},
               'description': {'xo': '20+ korporativ mobil ilova qurdim (Flutter, Clean Architecture, BLoC): '
                                     "yuklanishni ~40% tezlashtirdim, 15+ REST API, audio/video streaming, to'lov "
                                     "tizimla va murakkab animatsiyala. CI/CD yo'lga qo'yishda qatnashdim.",
                               'uz': 'Android va iOS uchun korporativ Flutter ilovalarini ishlab chiqdim. REST '
                                     'API, mahalliy saqlash, media, to‘lov interfeyslari va ko‘p tilli UI bilan '
                                     'ishladim. Keshlash va refaktoring orqali ilovalarni yaxshiladim; code '
                                     'review, CI/CD va reliz tayyorlashda qatnashdim.',
                               'ru': 'Разрабатывал корпоративные Flutter-приложения для Android и iOS. Работал с '
                                     'REST API, локальным хранением, медиа, платёжными интерфейсами и '
                                     'локализацией. Улучшал приложения через кеширование и рефакторинг; '
                                     'участвовал в ревью кода, CI/CD и подготовке релизов.',
                               'en': 'Developed corporate Flutter applications for Android and iOS. Implemented '
                                     'REST integrations, local storage, media playback, payment interfaces and '
                                     'multilingual UI. Improved responsiveness through caching and refactoring; '
                                     'contributed to code reviews, CI/CD and release preparation.'}}]


def set_translated(obj, field, values):
    for lang in LANGS:
        # Preserve the owner's existing Khorezm voice; initialize it only when empty.
        if lang == "xo" and getattr(obj, f"{field}_xo", None):
            continue
        attr = f"{field}_{lang}"
        if hasattr(obj, attr):
            setattr(obj, attr, values[lang])
        elif lang == "xo" and hasattr(obj, field):
            setattr(obj, field, values[lang])


class Command(BaseCommand):
    help = "Apply AI EdTech founder positioning to SiteSettings + Experience."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import SiteSettings

        obj = SiteSettings.load()
        for field, values in COPY.items():
            set_translated(obj, field, values)
        for field, value in PLAIN.items():
            if hasattr(obj, field):
                setattr(obj, field, value)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run complete: SiteSettings would be updated."))
            return

        obj.save()
        self.stdout.write(self.style.SUCCESS("AI EdTech founder positioning applied to SiteSettings."))

        from portfolio.models import Experience

        # Resume-sourced wording for existing timeline rows (matched, not created).
        for entry in EXPERIENCE:
            qs = Experience.objects.filter(company__icontains=entry["match"])
            if not qs.exists():
                self.stdout.write(self.style.WARNING(
                    f"Experience row matching '{entry['match']}' not found — skipped."
                ))
                continue
            for exp in qs:
                set_translated(exp, "position", entry["position"])
                set_translated(exp, "description", entry["description"])
                exp.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Updated experience: {exp.company} — {entry['position']['en']}"
                ))

        # Rewrite legacy "VibeCoder" identity in Experience timeline rows.
        # position is a translated field → patch every language column present.
        suffixes = ("_uz", "_ru", "_en")
        fixed = 0
        for exp in Experience.objects.all():
            changed = False
            for suffix in suffixes:
                attr = f"position{suffix}"
                val = getattr(exp, attr, None)
                if val and "VibeCoder" in val:
                    setattr(exp, attr, val.replace("VibeCoder", "AI EdTech Specialist"))
                    changed = True
            if changed:
                exp.save()
                fixed += 1
        if fixed:
            self.stdout.write(self.style.SUCCESS(
                f"Updated {fixed} Experience row(s): VibeCoder → AI EdTech Specialist."
            ))
