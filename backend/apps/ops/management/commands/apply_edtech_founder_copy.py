"""Apply jaysonkhan.com AI EdTech founder positioning.

Idempotent production command (deploy.sh runs it on EVERY deploy — these fields
are code-owned; admin hand-edits to them are overwritten). Keeps `xo` as the
default Khorezm dialect locale (owner's signature voice — man/mani, -la plural,
gal/girish), updates the SiteSettings singleton in all four locales
(xo, uz, ru, en), refreshes the Experience timeline wording from the 2026-07
resume, and rewrites any legacy "VibeCoder" Experience-timeline title.

Facts source (2026-07): resume + UzExam PTA-2026 docs — 3+ yrs experience,
25+ apps shipped (UIC 20+, freelance 5+), UzExam 60k+ questions / 5.2k users /
54 modules / 9 tracks, EduStats 52k+ verified Telegram users / 75 universities.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

LANGS = ("xo", "uz", "ru", "en")

COPY = {
    "site_title": {
        "xo": "Jayson Khan — O'zbekistonda AI EdTech Specialist | UzExam asoschisi",
        "uz": "Jayson Khan — O'zbekistonda AI EdTech Specialist | UzExam asoschisi",
        "ru": "Jayson Khan — AI EdTech специалист в Узбекистане | Основатель UzExam",
        "en": "Jayson Khan — AI EdTech Specialist in Uzbekistan | Founder of UzExam",
    },
    "site_tagline": {
        "xo": "AI yordamida EdTech mahsulotla, test platformala va ta'lim analitikasini quramiz.",
        "uz": "AI yordamida EdTech mahsulotlar, test platformalari va ta'lim analitikasini quramiz.",
        "ru": "AI-продукты для EdTech: тестовые платформы, образовательная аналитика и автоматизация.",
        "en": "AI-powered EdTech products, testing platforms and education analytics for Uzbekistan.",
    },
    "meta_description": {
        "xo": "Jayson Khan — UzExam va EduStats asoschisi. Bitta odam + 24/7 AI-agentla: 60k+ savolli test platforma, 52k+ auditoriyali ta'lim analitikasi va AI mentorla.",
        "uz": "Jayson Khan — UzExam va EduStats asoschisi. Bir odam + 24/7 AI-agentlar: 60k+ savolli test platforma, 52k+ auditoriyali ta'lim analitikasi va AI mentorlar.",
        "ru": "Jayson Khan — основатель UzExam и EduStats. Один человек + AI-агенты 24/7: тестовая платформа с 60k+ вопросов, образовательная аналитика с аудиторией 52k+ и AI-менторы.",
        "en": "Jayson Khan is an AI EdTech specialist and founder of UzExam and EduStats — one human + a 24/7 AI-agent workforce building a 60k+ question testing platform and education analytics in Uzbekistan.",
    },
    "meta_keywords": {
        "xo": "Jayson Khan, JaysonKhan, Jahongir Qo'ziboyev, Qo'ziboyev Jahongir, Kuziboyev Jahongir, AI EdTech Uzbekistan, UzExam asoschisi, EduStats, Edustats, test platforma O'zbekiston, ta'lim analitikasi, AI mentor, sun'iy intellekt mutaxassis O'zbekiston, solo AI founder",
        "uz": "Jayson Khan, JaysonKhan, Jahongir Qo'ziboyev, Qo'ziboyev Jahongir, Kuziboyev Jahongir, AI EdTech Uzbekistan, UzExam asoschisi, EduStats, Edustats, test platforma O'zbekiston, ta'lim analitikasi, AI mentor, sun'iy intellekt mutaxassis O'zbekiston, solo AI founder",
        "ru": "Jayson Khan, JaysonKhan, Жахонгир Кузибоев, Кузибоев Жахонгир, Джахонгир Кузибоев, AI EdTech Узбекистан, основатель UzExam, EduStats, Edustats, тестовая платформа, образовательная аналитика, AI mentor, AI специалист Узбекистан, solo AI founder",
        "en": "Jayson Khan, JaysonKhan, Jahongir Qoziboyev, Qoziboyev Jahongir, Kuziboyev Jahongir, AI EdTech Uzbekistan, UzExam founder, EduStats, Edustats, test platform Uzbekistan, education analytics, AI mentor, AI specialist Uzbekistan, solo AI founder",
    },
    "hero_eyebrow": {
        "xo": "AI EdTech · UzExam · EduStats · O'zbekiston",
        "uz": "AI EdTech · UzExam · EduStats · O'zbekiston",
        "ru": "AI EdTech · UzExam · EduStats · Узбекистан",
        "en": "AI EdTech · UzExam · EduStats · Uzbekistan",
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
        "xo": "Man Jayson Khan — UzExam va EduStats asoschisiman. Bitta odam + 24/7 AI-agentla bilan test platformala, AI mentorla va ta'lim analitikasi quraman. 60k+ savol, 55k+ foydalanuvchi — hammasi jonli production'da.",
        "uz": "Men Jayson Khan — UzExam va EduStats asoschisiman. Bir odam + 24/7 AI-agentlar bilan test platformalari, AI mentorlar va ta'lim analitikasi quraman. 60k+ savol, 55k+ foydalanuvchi — hammasi jonli production'da.",
        "ru": "Я Jayson Khan — основатель UzExam и EduStats. Один человек + AI-агенты 24/7: строю тестовые платформы, AI-менторов и образовательную аналитику. 60k+ вопросов, 55k+ пользователей — всё в живом production.",
        "en": "I'm Jayson Khan — founder of UzExam and EduStats. One human + a 24/7 AI-agent workforce building testing platforms, AI mentors and education analytics. 60k+ questions, 55k+ users — all in live production.",
    },
    "availability_badge": {
        "xo": "AI EdTech hamkorlikka ochiq",
        "uz": "AI EdTech hamkorlikka ochiq",
        "ru": "Открыт к AI EdTech партнёрствам",
        "en": "Open to AI EdTech partnerships",
    },
    "about_title": {
        "xo": "AI EdTech Founder",
        "uz": "AI EdTech Founder",
        "ru": "AI EdTech Founder",
        "en": "AI EdTech Founder",
    },
    "about_description": {
        "xo": "Man Jayson Khan (Jahongir Qo'ziboyev) — Xorazmdan chiqqan AI EdTech founder. Mobil davrda 3+ yilda 25+ ilova yetkazganman (UIC Group'da korporativ ilovala, TaxPay fintech). Endi studio davri: kod, QA, monitoring va incident-response — 24/7 AI-agentlada; strategiya, kontent sifati va mas'uliyat — manda. Natija: 3 oyda yolg'iz qurilgan UzExam (54 modul, 100k+ satr kod, 60k+ savol) va 52k+ tasdiqlangan auditoriyali EduStats. President Tech Award 2026 ishtirokchisiman.",
        "uz": "Men Jayson Khan (Jahongir Qo'ziboyev) — AI EdTech founder. Mobil davrda 3+ yilda 25+ ilova yetkazganman (UIC Group'da korporativ ilovalar, TaxPay fintech). Endi studio davri: kod, QA, monitoring va incident-response — 24/7 AI-agentlarda; strategiya, kontent sifati va mas'uliyat — menda. Natija: 3 oyda yolg'iz qurilgan UzExam (54 modul, 100k+ satr kod, 60k+ savol) va 52k+ tasdiqlangan auditoriyali EduStats. President Tech Award 2026 ishtirokchisiman.",
        "ru": "Я Jayson Khan (Жахонгир Кузибоев) — AI EdTech founder. В мобильную эру за 3+ года выпустил 25+ приложений (корпоративные приложения в UIC Group, финтех TaxPay). Теперь эра студии: код, QA, мониторинг и incident-response — на AI-агентах 24/7; стратегия, качество контента и ответственность — на мне. Результат: UzExam, построенный в одиночку за 3 месяца (54 модуля, 100k+ строк кода, 60k+ вопросов), и EduStats с верифицированной аудиторией 52k+. Участник President Tech Award 2026.",
        "en": "I'm Jayson Khan (Jahongir Qo'ziboyev) — an AI EdTech founder. In the mobile era I shipped 25+ apps over 3+ years (corporate apps at UIC Group, the TaxPay fintech). Now it's the studio era: code, QA, monitoring and incident response run on AI agents 24/7 — strategy, content quality and accountability stay with me. The result: UzExam built solo in 3 months (54 modules, 100k+ lines of code, 60k+ questions) and EduStats with a 52k+ verified audience. President Tech Award 2026 participant.",
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
        "xo": "Savollar bazasi (UzExam)",
        "uz": "Savollar bazasi (UzExam)",
        "ru": "База вопросов (UzExam)",
        "en": "Question bank (UzExam)",
    },
    "stat_4_label": {
        "xo": "Jami foydalanuvchila",
        "uz": "Jami foydalanuvchilar",
        "ru": "Всего пользователей",
        "en": "Users across products",
    },
    "featured_projects_title": {
        "xo": "AI EdTech ekotizimidagi asosiy mahsulotla.",
        "uz": "AI EdTech ekotizimidagi asosiy mahsulotlar.",
        "ru": "Ключевые продукты AI EdTech экосистемы.",
        "en": "Core products in the AI EdTech ecosystem.",
    },
    "projects_page_title": {
        "xo": "AI EdTech loyihala.",
        "uz": "AI EdTech loyihalar.",
        "ru": "AI EdTech проекты.",
        "en": "AI EdTech Projects.",
    },
    "projects_page_subtitle": {
        "xo": "UzExam, EduStats, AI mentorla, test platformala va ta'lim analitikasi bo'yicha mahsulotla.",
        "uz": "UzExam, EduStats, AI mentorlar, test platformalari va ta'lim analitikasi bo'yicha mahsulotlar.",
        "ru": "UzExam, EduStats, AI-менторы, тестовые платформы и продукты образовательной аналитики.",
        "en": "UzExam, EduStats, AI mentors, testing platforms and education analytics products.",
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
            {"q": "Jayson Khan kim?", "a": "Jayson Khan (Jahongir Qo'ziboyev) — O'zbekistonda AI EdTech mutaxassisi, UzExam va EduStats asoschisi. Test platformala, ta'lim analitikasi va AI mentor tizimlarini quradi. President Tech Award 2026 ishtirokchisi."},
            {"q": "UzExam nima?", "a": "UzExam (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi: 60k+ savol, 9 trek (DTM, IELTS, SAT, Avtotest va boshqala), takrorlanmas savolla (Uniqueness Engine), SM-2 va antifraud reyting. Telegram bilan chambarchas ishlaydi."},
            {"q": "EduStats nima?", "a": "EduStats (edustats.uz) — talabalar fikri va ta'lim analitikasi platformasi: universitetla reytingi, 52k+ telefon-tasdiqlangan Telegram auditoriyasi va 75 OTM o'tish ballari (2020–2025)."},
            {"q": "Bitta odam bularni qale eplaydi?", "a": "Arxitektura shunaqa: kod yozish, UI, QA, monitoring va tungi incident-response — 24/7 AI-agentlada. Strategiya, kontent sifati, mijozla va mas'uliyat — founderda. Shu tandem 3 oyda 54 modulli jonli platformani yolg'iz qurishga imkon berdi."},
            {"q": "Jayson Khan nimaga ixtisoslashgan?", "a": "Ta'limda AI, adaptiv test va imtihon platformala, ta'lim analitikasi, o'quvchi progressi, AI mentorla va mahsulot strategiyasi."},
            {"q": "Jayson Khan bilan qale bog'lansa bo'ladi?", "a": "jaysonkhan.com saytidagi kontakt sahifasi yo Telegram (@jaysonkhan) orqali — Telegram eng tez javob beradigan kanal."},
        ],
        "uz": [
            {"q": "Jayson Khan kim?", "a": "Jayson Khan (Jahongir Qo'ziboyev) — O'zbekistonda AI EdTech mutaxassisi, UzExam va EduStats asoschisi. Test platformalari, ta'lim analitikasi va AI mentor tizimlarini quradi. President Tech Award 2026 ishtirokchisi."},
            {"q": "UzExam nima?", "a": "UzExam (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi: 60k+ savol, 9 yo'nalish (DTM, IELTS, SAT, Avtotest va boshqalar), takrorlanmas savollar (Uniqueness Engine), SM-2 va antifraud reyting. Telegram bilan chuqur integratsiya."},
            {"q": "EduStats nima?", "a": "EduStats (edustats.uz) — talabalar fikri va ta'lim analitikasi platformasi: universitetlar reytingi, 52k+ telefon-tasdiqlangan Telegram auditoriyasi va 75 OTM o'tish ballari (2020–2025)."},
            {"q": "Bir odam bularning hammasini qanday uddalaydi?", "a": "Arxitektura shunday qurilgan: kod yozish, UI, QA, monitoring va tungi incident-response — 24/7 AI-agentlarda. Strategiya, kontent sifati, mijozlar va mas'uliyat — founderda. Shu tandem 3 oyda 54 modulli jonli platformani yolg'iz qurishga imkon berdi."},
            {"q": "Jayson Khan nimaga ixtisoslashgan?", "a": "Ta'limda AI, adaptiv test va imtihon platformalari, ta'lim analitikasi, o'quvchi progressi, AI mentorlar va mahsulot strategiyasi."},
            {"q": "Jayson Khan bilan qanday bog'lanish mumkin?", "a": "jaysonkhan.com saytidagi kontakt sahifasi yoki Telegram (@jaysonkhan) orqali — Telegram eng tez javob beradigan kanal."},
        ],
        "ru": [
            {"q": "Кто такой Jayson Khan?", "a": "Jayson Khan (Жахонгир Кузибоев) — AI EdTech специалист, основатель UzExam и EduStats из Ташкента, Узбекистан. Строит тестовые платформы, образовательную аналитику и системы AI-менторов. Участник President Tech Award 2026."},
            {"q": "Что такое UzExam?", "a": "UzExam (uzexam.uz) — универсальная адаптивная экзаменационная платформа для Узбекистана: 60k+ вопросов, 9 треков (DTM, IELTS, SAT, автотесты и другие), неповторяющиеся вопросы (Uniqueness Engine), SM-2 и антифрод-рейтинг. Глубокая интеграция с Telegram."},
            {"q": "Что такое EduStats?", "a": "EduStats (edustats.uz) — платформа студенческих отзывов и образовательной аналитики: рейтинги университетов, 52k+ верифицированная Telegram-аудитория и проходные баллы 75 вузов (2020–2025)."},
            {"q": "Как один человек справляется со всем этим?", "a": "Так устроена архитектура: код, UI, QA, мониторинг и ночной incident-response — на AI-агентах 24/7. Стратегия, качество контента, клиенты и ответственность — на основателе. Этот тандем позволил в одиночку построить живую платформу из 54 модулей за 3 месяца."},
            {"q": "На чём специализируется Jayson Khan?", "a": "AI в образовании, адаптивные тестовые и экзаменационные платформы, образовательная аналитика, прогресс студентов, AI-менторы и продуктовая стратегия."},
            {"q": "Как связаться с Jayson Khan?", "a": "Через страницу контактов на jaysonkhan.com или в Telegram (@jaysonkhan) — Telegram отвечает быстрее всего."},
        ],
        "en": [
            {"q": "Who is Jayson Khan?", "a": "Jayson Khan (Jahongir Qo'ziboyev) is an AI EdTech specialist and founder of UzExam and EduStats, based in Tashkent, Uzbekistan. He builds testing platforms, education analytics and AI mentor systems. President Tech Award 2026 participant."},
            {"q": "What is UzExam?", "a": "UzExam (uzexam.uz) is a universal, adaptive exam platform for Uzbekistan: 60k+ questions across 9 tracks (DTM, IELTS, SAT, driving tests and more), non-repeating questions (Uniqueness Engine), SM-2 spaced repetition and an anti-fraud rating. Deeply integrated with Telegram."},
            {"q": "What is EduStats?", "a": "EduStats (edustats.uz) is a student-voice and education-analytics platform: university rankings, a 52k+ phone-verified Telegram audience and admission cut-off scores for 75 universities (2020–2025)."},
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
    # 3+ years · 25+ apps · 60k+ questions · 55k+ users (52k EduStats + 5.2k UzExam)
    "stat_1_count": 3,
    "stat_1_suffix": "+",
    "stat_2_count": 25,
    "stat_2_suffix": "+",
    "stat_3_count": 60,
    "stat_3_suffix": "k+",
    "stat_4_count": 55,
    "stat_4_suffix": "k+",
}

# Experience timeline wording from the 2026-07 resume. Rows are matched by
# `company__icontains` and NEVER created here (rows/dates stay admin-owned) —
# only position/description wording is code-owned.
EXPERIENCE = [
    {
        "match": "UzExam",
        "position": {
            "xo": "Founder & AI EdTech Specialist",
            "uz": "Founder & AI EdTech Specialist",
            "ru": "Founder & AI EdTech Specialist",
            "en": "Founder & AI EdTech Specialist",
        },
        "description": {
            "xo": "UzExam.uz'ni noldan qurdim — 54 modul, 60k+ savol, 9 imtihon treki, B2B tenant tizimi, Click/Stars to'lovla. Kod, QA, monitoring va incident-response — 24/7 AI-agentlada; strategiya va sifat nazorati manda. President Tech Award 2026 ishtirokchisi.",
            "uz": "UzExam.uz'ni noldan qurdim — 54 modul, 60k+ savol, 9 imtihon yo'nalishi, B2B tenant tizimi, Click/Stars to'lovlar. Kod, QA, monitoring va incident-response — 24/7 AI-agentlarda; strategiya va sifat nazorati menda. President Tech Award 2026 ishtirokchisi.",
            "ru": "Построил UzExam.uz с нуля — 54 модуля, 60k+ вопросов, 9 экзаменационных треков, B2B-tenant система, платежи Click/Stars. Код, QA, мониторинг и incident-response — на AI-агентах 24/7; стратегия и контроль качества — на мне. Участник President Tech Award 2026.",
            "en": "Built UzExam.uz from zero — 54 modules, 60k+ questions, 9 exam tracks, B2B tenants, Click/Stars payments. Code, QA, monitoring and incident response run on AI agents 24/7; strategy and quality control stay with me. President Tech Award 2026 participant.",
        },
    },
    {
        "match": "Soliq",
        "position": {
            "xo": "Software Engineer — Flutter / Fintech",
            "uz": "Software Engineer — Flutter / Fintech",
            "ru": "Software Engineer — Flutter / Fintech",
            "en": "Software Engineer — Flutter / Fintech",
        },
        "description": {
            "xo": "TaxPay fintech to'lov ilovasini noldan qurdim: Flutter + Clean Architecture, karta ulash, OTP, tranzaksiyala va PCI talablariga mos REST integratsiyala. Ilova production-ready darajaga yetkazildi.",
            "uz": "TaxPay fintech to'lov ilovasini noldan qurdim: Flutter + Clean Architecture, karta ulash, OTP, tranzaksiyalar va PCI talablariga mos REST integratsiyalar. Ilova production-ready darajaga yetkazildi.",
            "ru": "Построил финтех-приложение TaxPay с нуля: Flutter + Clean Architecture, привязка карт, OTP, транзакции и PCI-совместимые REST-интеграции. Доведено до production-ready уровня.",
            "en": "Built TaxPay, a fintech payment app, from scratch: Flutter + Clean Architecture, card binding, OTP, transaction processing and PCI-aware REST integrations. Delivered to production-ready stage.",
        },
    },
    {
        "match": "AIBA",
        "position": {
            "xo": "Mobile Team Lead — AI Business Assistant",
            "uz": "Mobile Team Lead — AI Business Assistant",
            "ru": "Mobile Team Lead — AI Business Assistant",
            "en": "Mobile Team Lead — AI Business Assistant",
        },
        "description": {
            "xo": "AIBA loyihasida mobil jamoaga yetakchilik qildim: AI vositala, generativ servisla va aqlli assistent funksiyalarini mobil ilovalarga qo'shdik; code review va mentorlik manda edi.",
            "uz": "AIBA loyihasida mobil jamoaga yetakchilik qildim: AI vositalar, generativ servislar va aqlli assistent funksiyalarini mobil ilovalarga qo'shdik; code review va mentorlik menda edi.",
            "ru": "Возглавлял мобильную команду проекта AIBA: интегрировали AI-инструменты, генеративные сервисы и функции интеллектуального ассистента в мобильные приложения; вёл code review и менторил инженеров.",
            "en": "Led the mobile team on AIBA: integrated AI tools, generative services and intelligent assistant features into mobile apps; ran code reviews and mentored engineers.",
        },
    },
    {
        "match": "UIC",
        "position": {
            "xo": "Flutter Mobile Engineer",
            "uz": "Flutter Mobile Engineer",
            "ru": "Flutter Mobile Engineer",
            "en": "Flutter Mobile Engineer",
        },
        "description": {
            "xo": "20+ korporativ mobil ilova qurdim (Flutter, Clean Architecture, BLoC): yuklanishni ~40% tezlashtirdim, 15+ REST API, audio/video streaming, to'lov tizimla va murakkab animatsiyala. CI/CD yo'lga qo'yishda qatnashdim.",
            "uz": "20+ korporativ mobil ilova qurdim (Flutter, Clean Architecture, BLoC): yuklanishni ~40% tezlashtirdim, 15+ REST API, audio/video streaming, to'lov tizimlari va murakkab animatsiyalar. CI/CD yo'lga qo'yishda qatnashdim.",
            "ru": "Разработал 20+ корпоративных мобильных приложений (Flutter, Clean Architecture, BLoC): ускорил загрузку на ~40%, 15+ REST API, аудио/видео стриминг, платёжные системы и сложные анимации. Участвовал в настройке CI/CD.",
            "en": "Developed 20+ corporate mobile apps (Flutter, Clean Architecture, BLoC): cut load times ~40%, integrated 15+ REST APIs, built audio/video streaming, payment systems and complex animations. Helped establish CI/CD pipelines.",
        },
    },
]


def set_translated(obj, field, values):
    for lang in LANGS:
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
        suffixes = ("", "_xo", "_uz", "_ru", "_en")
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
