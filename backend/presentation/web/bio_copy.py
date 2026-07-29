"""Code-owned bio-page copy in all four locales (xo, uz, ru, en).

Why a Python dict and not SiteSettings/`{% trans %}`:
  • This page is an SEO asset, not editorial content — it must stay stable and
    reviewable in git diffs, and it must never be half-overwritten by a seeder.
  • Storing it in SiteSettings would mean ~20 new translated columns + a
    migration + an admin tab for a single page. Storing it in django.po would
    scatter one page's prose across four .po files.

Target queries this page exists to answer (all four scripts):
    Jahongir Qo'ziboyev · Qo'ziboyev Jahongir · Жаҳонгир Қўзибоев ·
    Жахонгир Кузибоев · Jayson Khan · AI dasturchi · mobil dasturchi ·
    full stack dasturchi · Flutter dasturchi · AI разработчик ·
    мобильный разработчик · AI developer · mobile developer

EVERY factual claim here is sourced from copy already shipped in
`ops/management/commands/apply_edtech_founder_copy.py` (2026-07 resume +
UzExam PTA-2026 docs). Do not add numbers or credentials that are not
already asserted there.

`xo` is the Khorezm dialect — the owner's signature voice (-la plural,
man/mani, gal/girish, qale). Reword only after the owner approves.
"""
from __future__ import annotations

# ── Name variants (identical in every locale — this is the disambiguation
#    block, its whole point is showing all spellings side by side) ──────────
NAME_GROUPS = [
    {
        "label": "Lotin / Latin",
        "names": ["Jahongir Qo'ziboyev", "Qo'ziboyev Jahongir",
                  "Jahongir Kuziboev", "Jahongir Quziboyev"],
    },
    {
        "label": "Кирилл (ўзбек)",
        "names": ["Жаҳонгир Қўзибоев", "Қўзибоев Жаҳонгир"],
    },
    {
        "label": "Кириллица (рус.)",
        "names": ["Жахонгир Кузибоев", "Кузибоев Жахонгир",
                  "Джахонгир Кузибоев"],
    },
    {
        "label": "Brand / Бренд",
        "names": ["Jayson Khan", "JaysonKhan", "Жейсон Хан", "@jaysonkhan"],
    },
]

SKILL_GROUPS = [
    ("Mobile", "Flutter · Dart · Clean Architecture · BLoC · iOS · Android"),
    ("Backend", "Python · Django · DRF · FastAPI · aiogram · PostgreSQL · Redis"),
    ("AI", "AI-agent orchestration · Claude Code · AI mentor systems · AI-assisted engineering"),
    ("Web / DevOps", "JavaScript · TypeScript · HTMX · Nginx · Linux · CI/CD"),
]

BIO = {
    # ── XO — Khorezm dialect, owner's signature voice ────────────────────
    "xo": {
        "seo_title": "Jahongir Qo'ziboyev (Jayson Khan) — AI, mobil va full-stack dasturchi",
        "meta_description": (
            "Jahongir Qo'ziboyev (Jayson Khan) — Xorazmdan chiqqan AI, mobil va "
            "full-stack dasturchi, UzExam va EduStats asoschisi. 25+ ilova, 60k+ savol."
        ),
        "eyebrow": "Kim u? · AI · Mobil · Full-stack · Toshkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            "Man Jahongir Qo'ziboyev — internetda Jayson Khan nomi bilan tanilganman. "
            "Xorazmdan chiqqanman, Toshkentda ishlayman. Mobil dasturchi bo'lib boshlab, "
            "3+ yilda 25+ ilova yetkazganman; endi AI dasturchi va EdTech founder sifatida "
            "24/7 AI-agentla bilan test platformala, ta'lim analitikasi va AI mentorla quraman."
        ),
        "sections": [
            {
                "h2": "Mobil dasturchilikdan AI dasturchilikkacha",
                "body": [
                    "Yo'lni Flutter mobil dasturchi bo'lib boshlaganman. UIC Group'da 20+ korporativ "
                    "mobil ilova qurdim — Clean Architecture va BLoC, yuklanish ~40% tez, 15+ REST API, "
                    "audio/video streaming, to'lov tizimla va murakkab animatsiyala; CI/CD yo'lga "
                    "qo'yishda ham qatnashdim.",
                    "Keyin AIBA (AI Business Assistant) loyihasida mobil jamoaga yetakchilik qildim: "
                    "AI vositala va generativ servisla mobil ilovalarga qo'shildi, code review va "
                    "mentorlik manda edi. Soliq yo'nalishida TaxPay fintech to'lov ilovasini noldan "
                    "qurdim — Flutter, karta ulash, OTP, tranzaksiyala va PCI talablariga mos REST "
                    "integratsiyala.",
                    "Bugun full-stack ishlayman: mobil oldingi tajriba ustiga Python/Django backend, "
                    "PostgreSQL, Nginx va Linux server boshqaruvi qo'shildi. Kod, QA, monitoring va "
                    "tungi incident-response — 24/7 AI-agentlada; strategiya, kontent sifati va "
                    "mas'uliyat — manda.",
                ],
            },
            {
                "h2": "Nima quraman",
                "body": [
                    "UzExam (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi. "
                    "3 oyda yolg'iz qurilgan: 54 modul, 100k+ satr kod, 60k+ savol, 9 imtihon treki "
                    "(DTM, IELTS, SAT, Avtotest va boshqala), takrorlanmas savolla (Uniqueness Engine), "
                    "SM-2 takrorlash, antifraud reyting, B2B tenant tizimi va Click/Stars to'lovla.",
                    "EduStats (edustats.uz) — talabalar fikri va ta'lim analitikasi platformasi: "
                    "universitetla reytingi, 52k+ telefon-tasdiqlangan Telegram auditoriyasi va "
                    "75 OTM o'tish ballari (2020–2025).",
                    "Ikkalasi ham jonli production'da ishlayapti. President Tech Award 2026 "
                    "ishtirokchisiman.",
                ],
            },
        ],
        "aka_title": "Ism variantlari",
        "aka_intro": (
            "Ismim alifbo va transliteratsiyaga qarab har xil yoziladi. Qidiruvda topish "
            "oson bo'lsin uchun asosiy variantla:"
        ),
        "skills_title": "Texnologiyala",
        "faq_title": "Ko'p so'raladigan savolla",
        "faq": [
            {
                "q": "Jahongir Qo'ziboyev kim?",
                "a": "Jahongir Qo'ziboyev (Jayson Khan) — O'zbekistonda ishlaydigan AI, mobil va "
                     "full-stack dasturchi, UzExam va EduStats asoschisi. Xorazmdan, Toshkentda "
                     "yashaydi. President Tech Award 2026 ishtirokchisi.",
            },
            {
                "q": "Jahongir Qo'ziboyev va Jayson Khan bir odammi?",
                "a": "Ha. Jayson Khan — internetdagi brend nomim; pasportdagi ismim Jahongir "
                     "Qo'ziboyev. Kirilda Жаҳонгир Қўзибоев, ruschada Жахонгир Кузибоев deb yoziladi.",
            },
            {
                "q": "Qanaqa dasturchi?",
                "a": "Mobil tomondan Flutter/Dart (25+ ilova), backend tomondan Python/Django va "
                     "FastAPI, ustiga AI-agent orkestratsiyasi. Ya'ni mobil dasturchi + full-stack "
                     "dasturchi + AI dasturchi — uchalasi bitta odamda.",
            },
            {
                "q": "Qaysi ilovalarni qurgan?",
                "a": "UIC Group'da 20+ korporativ mobil ilova, AIBA'da AI assistent funksiyala, "
                     "TaxPay fintech to'lov ilovasi, keyin o'z mahsulotlarim — UzExam va EduStats.",
            },
            {
                "q": "Qanday bog'lansa bo'ladi?",
                "a": "jaysonkhan.com kontakt sahifasi yo Telegram (@jaysonkhan) orqali — Telegram "
                     "eng tez javob beradigan kanal.",
            },
        ],
        "cta_title": "Loyiha bormi?",
        "cta_text": "Mobil ilova, AI mahsulot yo EdTech platforma — brifni tashlang, qolganini surishtiraman.",
        "cta_btn": "Bog'lanish",
    },

    # ── UZ — standard Latin Uzbek ────────────────────────────────────────
    "uz": {
        "seo_title": "Jahongir Qo'ziboyev (Jayson Khan) — AI, mobil va full-stack dasturchi",
        "meta_description": (
            "Jahongir Qo'ziboyev (Jayson Khan) — O'zbekistonda AI, mobil va full-stack "
            "dasturchi, UzExam va EduStats asoschisi. 25+ ilova, 60k+ savol, 55k+ foydalanuvchi."
        ),
        "eyebrow": "Men haqimda · AI · Mobil · Full-stack · Toshkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            "Men Jahongir Qo'ziboyev — internetda Jayson Khan nomi bilan tanilganman. "
            "Xorazmdanman, Toshkentda ishlayman. Mobil dasturchi bo'lib boshlab, 3+ yilda "
            "25+ ilova yetkazganman; hozir AI dasturchi va EdTech founder sifatida 24/7 "
            "AI-agentlar bilan test platformalari, ta'lim analitikasi va AI mentorlar quraman."
        ),
        "sections": [
            {
                "h2": "Mobil dasturchilikdan AI dasturchilikkacha",
                "body": [
                    "Yo'lni Flutter mobil dasturchi sifatida boshladim. UIC Group'da 20+ korporativ "
                    "mobil ilova qurdim — Clean Architecture va BLoC, yuklanish ~40% tezroq, 15+ REST "
                    "API, audio/video streaming, to'lov tizimlari va murakkab animatsiyalar; CI/CD "
                    "yo'lga qo'yishda ham qatnashdim.",
                    "So'ng AIBA (AI Business Assistant) loyihasida mobil jamoaga yetakchilik qildim: "
                    "AI vositalar va generativ servislar mobil ilovalarga integratsiya qilindi, code "
                    "review va mentorlik mendan edi. Soliq yo'nalishida TaxPay fintech to'lov ilovasini "
                    "noldan qurdim — Flutter, karta ulash, OTP, tranzaksiyalar va PCI talablariga mos "
                    "REST integratsiyalar.",
                    "Bugun full-stack ishlayman: mobil tajriba ustiga Python/Django backend, "
                    "PostgreSQL, Nginx va Linux server boshqaruvi qo'shildi. Kod, QA, monitoring va "
                    "tungi incident-response — 24/7 AI-agentlarda; strategiya, kontent sifati va "
                    "mas'uliyat — menda.",
                ],
            },
            {
                "h2": "Nima quraman",
                "body": [
                    "UzExam (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi. "
                    "3 oyda yolg'iz qurilgan: 54 modul, 100k+ satr kod, 60k+ savol, 9 yo'nalish "
                    "(DTM, IELTS, SAT, Avtotest va boshqalar), takrorlanmas savollar (Uniqueness "
                    "Engine), SM-2 takrorlash, antifraud reyting, B2B tenant tizimi va Click/Stars "
                    "to'lovlari.",
                    "EduStats (edustats.uz) — talabalar fikri va ta'lim analitikasi platformasi: "
                    "universitetlar reytingi, 52k+ telefon-tasdiqlangan Telegram auditoriyasi va "
                    "75 OTM o'tish ballari (2020–2025).",
                    "Ikkalasi ham jonli production'da. President Tech Award 2026 ishtirokchisiman.",
                ],
            },
        ],
        "aka_title": "Ism variantlari",
        "aka_intro": (
            "Ismim alifbo va transliteratsiyaga qarab turlicha yoziladi. Qidiruvda topish "
            "oson bo'lishi uchun asosiy variantlar:"
        ),
        "skills_title": "Texnologiyalar",
        "faq_title": "Ko'p so'raladigan savollar",
        "faq": [
            {
                "q": "Jahongir Qo'ziboyev kim?",
                "a": "Jahongir Qo'ziboyev (Jayson Khan) — O'zbekistonda ishlaydigan AI, mobil va "
                     "full-stack dasturchi, UzExam va EduStats asoschisi. Xorazmdan, Toshkentda "
                     "yashaydi. President Tech Award 2026 ishtirokchisi.",
            },
            {
                "q": "Jahongir Qo'ziboyev va Jayson Khan bir odammi?",
                "a": "Ha. Jayson Khan — internetdagi brend nomim; pasportdagi ismim Jahongir "
                     "Qo'ziboyev. Kirilda Жаҳонгир Қўзибоев, ruschada Жахонгир Кузибоев deb yoziladi.",
            },
            {
                "q": "U qanday dasturchi?",
                "a": "Mobil tomondan Flutter/Dart (25+ ilova), backend tomondan Python/Django va "
                     "FastAPI, ustiga AI-agent orkestratsiyasi. Ya'ni mobil dasturchi + full-stack "
                     "dasturchi + AI dasturchi bitta odamda.",
            },
            {
                "q": "Qaysi ilovalarni qurgan?",
                "a": "UIC Group'da 20+ korporativ mobil ilova, AIBA'da AI assistent funksiyalari, "
                     "TaxPay fintech to'lov ilovasi, keyin o'z mahsulotlari — UzExam va EduStats.",
            },
            {
                "q": "Qanday bog'lanish mumkin?",
                "a": "jaysonkhan.com kontakt sahifasi yoki Telegram (@jaysonkhan) orqali — Telegram "
                     "eng tez javob beradigan kanal.",
            },
        ],
        "cta_title": "Loyihangiz bormi?",
        "cta_text": "Mobil ilova, AI mahsulot yoki EdTech platforma — brifni tashlang, qolganini o'zim aniqlayman.",
        "cta_btn": "Bog'lanish",
    },

    # ── RU ───────────────────────────────────────────────────────────────
    "ru": {
        "seo_title": "Жахонгир Кузибоев (Jayson Khan) — AI, мобильный и full-stack разработчик",
        "meta_description": (
            "Жахонгир Кузибоев (Jayson Khan) — AI, мобильный и full-stack разработчик из "
            "Узбекистана, основатель UzExam и EduStats. 25+ приложений, 60k+ вопросов."
        ),
        "eyebrow": "Обо мне · AI · Mobile · Full-stack · Ташкент",
        "h1": "Жахонгир Кузибоев",
        "h1_em": "(Jayson Khan)",
        "lede": (
            "Меня зовут Жахонгир Кузибоев — в интернете я известен как Jayson Khan. "
            "Родом из Хорезма, работаю в Ташкенте. Начинал как мобильный разработчик и за "
            "3+ года выпустил 25+ приложений; сейчас — AI-разработчик и EdTech-основатель: "
            "строю тестовые платформы, образовательную аналитику и AI-менторов вместе с "
            "AI-агентами 24/7."
        ),
        "sections": [
            {
                "h2": "От мобильной разработки к AI-разработке",
                "body": [
                    "Начинал как Flutter-разработчик. В UIC Group сделал 20+ корпоративных мобильных "
                    "приложений — Clean Architecture и BLoC, ускорение загрузки на ~40%, 15+ REST API, "
                    "аудио/видео стриминг, платёжные системы и сложные анимации; участвовал в "
                    "настройке CI/CD.",
                    "Затем возглавлял мобильную команду проекта AIBA (AI Business Assistant): "
                    "интегрировали AI-инструменты и генеративные сервисы в мобильные приложения, "
                    "вёл code review и менторил инженеров. В налоговом направлении построил с нуля "
                    "финтех-приложение TaxPay — Flutter, привязка карт, OTP, транзакции и "
                    "PCI-совместимые REST-интеграции.",
                    "Сегодня работаю как full-stack разработчик: к мобильному опыту добавились "
                    "Python/Django бэкенд, PostgreSQL, Nginx и администрирование Linux-серверов. "
                    "Код, QA, мониторинг и ночной incident-response — на AI-агентах 24/7; стратегия, "
                    "качество контента и ответственность — на мне.",
                ],
            },
            {
                "h2": "Что я строю",
                "body": [
                    "UzExam (uzexam.uz) — универсальная адаптивная экзаменационная платформа для "
                    "Узбекистана. Построена в одиночку за 3 месяца: 54 модуля, 100k+ строк кода, "
                    "60k+ вопросов, 9 экзаменационных треков (DTM, IELTS, SAT, автотесты и другие), "
                    "неповторяющиеся вопросы (Uniqueness Engine), интервальное повторение SM-2, "
                    "антифрод-рейтинг, B2B-tenant система и платежи Click/Stars.",
                    "EduStats (edustats.uz) — платформа студенческих отзывов и образовательной "
                    "аналитики: рейтинги университетов, 52k+ верифицированная по телефону "
                    "Telegram-аудитория и проходные баллы 75 вузов (2020–2025).",
                    "Оба продукта работают в живом production. Участник President Tech Award 2026.",
                ],
            },
        ],
        "aka_title": "Варианты написания имени",
        "aka_intro": (
            "Моё имя пишется по-разному в зависимости от алфавита и транслитерации. "
            "Основные варианты — чтобы меня было проще найти в поиске:"
        ),
        "skills_title": "Технологии",
        "faq_title": "Часто задаваемые вопросы",
        "faq": [
            {
                "q": "Кто такой Жахонгир Кузибоев?",
                "a": "Жахонгир Кузибоев (Jayson Khan) — AI, мобильный и full-stack разработчик из "
                     "Узбекистана, основатель UzExam и EduStats. Родом из Хорезма, живёт в Ташкенте. "
                     "Участник President Tech Award 2026.",
            },
            {
                "q": "Жахонгир Кузибоев и Jayson Khan — один человек?",
                "a": "Да. Jayson Khan — мой бренд в интернете; имя по паспорту — Jahongir Qo'ziboyev, "
                     "по-русски Жахонгир Кузибоев, узбекской кириллицей Жаҳонгир Қўзибоев.",
            },
            {
                "q": "Какой он разработчик?",
                "a": "Мобильная часть — Flutter/Dart (25+ приложений), бэкенд — Python/Django и "
                     "FastAPI, сверху оркестрация AI-агентов. То есть мобильный разработчик + "
                     "full-stack разработчик + AI-разработчик в одном человеке.",
            },
            {
                "q": "Какие приложения он сделал?",
                "a": "20+ корпоративных мобильных приложений в UIC Group, AI-ассистент функции в AIBA, "
                     "финтех-приложение TaxPay, затем собственные продукты — UzExam и EduStats.",
            },
            {
                "q": "Как с ним связаться?",
                "a": "Через страницу контактов на jaysonkhan.com или в Telegram (@jaysonkhan) — "
                     "Telegram отвечает быстрее всего.",
            },
        ],
        "cta_title": "Есть проект?",
        "cta_text": "Мобильное приложение, AI-продукт или EdTech-платформа — пришлите бриф, остальное уточню сам.",
        "cta_btn": "Связаться",
    },

    # ── EN ───────────────────────────────────────────────────────────────
    "en": {
        "seo_title": "Jahongir Qo'ziboyev (Jayson Khan) — AI, Mobile & Full-Stack Developer",
        "meta_description": (
            "Jahongir Qo'ziboyev (Jayson Khan) is an AI, mobile and full-stack developer "
            "from Uzbekistan, founder of UzExam and EduStats. 25+ apps, 60k+ questions."
        ),
        "eyebrow": "About · AI · Mobile · Full-stack · Tashkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            "I'm Jahongir Qo'ziboyev — known online as Jayson Khan. Born in Khorezm, based "
            "in Tashkent. I started as a mobile developer and shipped 25+ apps over 3+ years; "
            "today I work as an AI developer and EdTech founder, building testing platforms, "
            "education analytics and AI mentors alongside a 24/7 AI-agent workforce."
        ),
        "sections": [
            {
                "h2": "From mobile development to AI development",
                "body": [
                    "I started as a Flutter mobile developer. At UIC Group I built 20+ corporate "
                    "mobile apps — Clean Architecture and BLoC, ~40% faster load times, 15+ REST API "
                    "integrations, audio/video streaming, payment systems and complex animations; "
                    "I also helped establish CI/CD pipelines.",
                    "I then led the mobile team on AIBA (AI Business Assistant): integrating AI tools "
                    "and generative services into mobile apps, running code reviews and mentoring "
                    "engineers. On the tax side I built TaxPay, a fintech payment app, from scratch — "
                    "Flutter, card binding, OTP, transaction processing and PCI-aware REST "
                    "integrations.",
                    "Today I work full-stack: on top of the mobile experience came Python/Django "
                    "backends, PostgreSQL, Nginx and Linux server administration. Code, QA, "
                    "monitoring and 3 AM incident response run on AI agents 24/7; strategy, content "
                    "quality and accountability stay with me.",
                ],
            },
            {
                "h2": "What I build",
                "body": [
                    "UzExam (uzexam.uz) — a universal, adaptive exam platform for Uzbekistan. Built "
                    "solo in 3 months: 54 modules, 100k+ lines of code, 60k+ questions, 9 exam tracks "
                    "(DTM, IELTS, SAT, driving tests and more), non-repeating questions (Uniqueness "
                    "Engine), SM-2 spaced repetition, an anti-fraud rating, B2B tenants and "
                    "Click/Stars payments.",
                    "EduStats (edustats.uz) — a student-voice and education-analytics platform: "
                    "university rankings, a 52k+ phone-verified Telegram audience and admission "
                    "cut-off scores for 75 universities (2020–2025).",
                    "Both run in live production. President Tech Award 2026 participant.",
                ],
            },
        ],
        "aka_title": "Name variants",
        "aka_intro": (
            "My name is spelled differently depending on the alphabet and transliteration. "
            "The main variants, so I'm easier to find in search:"
        ),
        "skills_title": "Technologies",
        "faq_title": "Frequently asked questions",
        "faq": [
            {
                "q": "Who is Jahongir Qo'ziboyev?",
                "a": "Jahongir Qo'ziboyev (Jayson Khan) is an AI, mobile and full-stack developer "
                     "based in Uzbekistan and the founder of UzExam and EduStats. Born in Khorezm, "
                     "based in Tashkent. President Tech Award 2026 participant.",
            },
            {
                "q": "Are Jahongir Qo'ziboyev and Jayson Khan the same person?",
                "a": "Yes. Jayson Khan is my online brand name; my legal name is Jahongir Qo'ziboyev — "
                     "Жаҳонгир Қўзибоев in Uzbek Cyrillic, Жахонгир Кузибоев in Russian.",
            },
            {
                "q": "What kind of developer is he?",
                "a": "Flutter/Dart on mobile (25+ apps), Python/Django and FastAPI on the backend, "
                     "with AI-agent orchestration on top. In other words: mobile developer + "
                     "full-stack developer + AI developer in one person.",
            },
            {
                "q": "Which apps has he built?",
                "a": "20+ corporate mobile apps at UIC Group, AI assistant features on AIBA, the "
                     "TaxPay fintech payment app, and then his own products — UzExam and EduStats.",
            },
            {
                "q": "How can I contact him?",
                "a": "Through the contact page on jaysonkhan.com or via Telegram (@jaysonkhan) — "
                     "Telegram is the fastest channel.",
            },
        ],
        "cta_title": "Got a project?",
        "cta_text": "A mobile app, an AI product or an EdTech platform — send the brief, I'll take it from there.",
        "cta_btn": "Get in touch",
    },
}


def get_bio(lang_code: str) -> dict:
    """Return the bio block for `lang_code`, falling back to the xo default."""
    return BIO.get(lang_code) or BIO["xo"]
