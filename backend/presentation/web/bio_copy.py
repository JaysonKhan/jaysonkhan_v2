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
UzExam PTA-2026 docs). Product counts were refreshed on 2026-09-21 from
read-only production aggregates; see docs/project-facts-2026-09.md.

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
            "Jahongir Qo'ziboyev (Jayson Khan) — Xorazmdan chiqqan AI, mobil va full-stack dasturchi, UzExam va"
            " EduStats asoschisi. 25+ ilova, 85k+ savol."
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
                    "UzExam (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi. 3 "
                    "oyda yolg'iz qurilgan: 7 mobil ilova, 21k+ ro'yxatdan o'tgan foydalanuvchi, 85k+ "
                    "ochiq savol, imtihon yo‘nalishla (DTM, IELTS, SAT, Avtotest va boshqala), "
                    "takrorlanmas savolla (Uniqueness Engine), SM-2 takrorlash, antifraud reyting, B2B "
                    "tenant tizimi va Click/Stars to'lovla.",
                    "EduStats (edustats.uz) — talabalar fikri va ta'lim analitikasi platformasi: "
                    "universitetla reytingi, 53k+ Telegram auditoriyasi va 121 OTM o'tish"
                    " ballari (2020–2025).",
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
            ('Jahongir Qo‘ziboyev (Jayson Khan) — Consort Group’da Mobile Developer va UzExam asoschisi. Flutter '
             'ilovalari, Django platformalari va EduStats.')
        ),
        "eyebrow": "Men haqimda · AI · Mobil · Full-stack · Toshkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            ('Consort Group’da Mobile Developer sifatida Growz va Bizon ilovalariga AI va xarita funksiyalarini '
             'qo‘shish ustida ishlayman. UzExam asoschisiman: yettita Flutter ilovasi va Django platformasini '
             'rivojlantiraman. EduStats ham o‘z loyiham.')
        ),
        "sections": [
            {
                "h2": 'Ish tajribasi va ta’lim',
                "body": ['2026-yil iyunidan Consort Group’da Mobile Developer bo‘lib ishlayman. Growz va Bizon Flutter '
                         'ilovalariga AI integratsiya qilish va xarita funksiyalarini rivojlantirish bilan shug‘ullanaman.',
                         '2026-yil yanvar–aprel oylarida Soliq servis AJ’da TaxPay’ni Flutter, Clean Architecture va BLoC '
                         'asosida qurdim. Karta ulash, OTP, to‘lovlar va tranzaksiyalar tarixini ishlab chiqdim. Ilova ishga '
                         'tushirishga tayyor holatga yetdi, ammo bo‘lim yopilgach ommaga chiqarilmadi.',
                         '2023-yil sentabridan 2025-yil dekabrigacha UIC Group’da Android va iOS uchun Flutter ilovalari, '
                         'API integratsiyalari va ilova unumdorligi ustida ishladim. Shu davrda AI Business Assistant '
                         'loyihasida ham (2025-yil avgust–noyabr) assistent funksiyalarini ishlab chiqdim va mobil jamoa '
                         'vazifalarini muvofiqlashtirdim.',
                         '2026-yilda Toshkent axborot texnologiyalari universitetining Dasturiy injiniring yo‘nalishini '
                         'bakalavr darajasi bilan tamomladim. Hozirgi ishlarim Flutter ilovalari, Django API, PostgreSQL, '
                         'Redis va o‘z mahsulotlarimni doimiy rivojlantirishni qamrab oladi.'],
            },
            {
                "h2": "Nima quraman",
                "body": [
                    "UzExam — 85k+ ochiq savol, 21k+ ro'yxatdan o'tgan foydalanuvchi va 7 mobil ilova. IELTS, "
                    "Multilevel, SAT, DTM, Milliy sertifikat, Avtotest va Intervyu — web, Telegram va "
                    "Flutter'da.",
                    "EduStats — 53k+ Telegram foydalanuvchi, katalogda 193 faol OTM va 121 OTM bo'yicha o'tish "
                    "ballari. Talabalar fikri, reytinglar va manbali ta'lim statistikasi bir joyda.",
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
                "a": ('Toshkentda Consort Group’da ishlaydigan Mobile Developer va UzExam asoschisi. EduStats’ni ham '
                      'yaratganman. Jahongir Qo‘ziboyev va Jayson Khan — bir inson.'),
            },
            {
                "q": "Jahongir Qo'ziboyev va Jayson Khan bir odammi?",
                "a": "Ha. Jayson Khan — internetdagi brend nomim; pasportdagi ismim Jahongir "
                     "Qo'ziboyev. Kirilda Жаҳонгир Қўзибоев, ruschada Жахонгир Кузибоев deb yoziladi.",
            },
            {
                "q": "U qanday dasturchi?",
                "a": ('Flutter’da Android va iOS ilovalari, Python va Django’da backend servislarini yarataman. Hozir AI '
                      'integratsiyalari, xaritalar, imtihonga tayyorgarlik va ta’lim ma’lumotlari bilan ishlayman.'),
            },
            {
                "q": "Qaysi ilovalarni qurgan?",
                "a": ('Consort Group’da Growz va Bizon, Soliq servis AJ’da TaxPay, UIC Group’da korporativ Flutter '
                      'ilovalari va AI Business Assistant. O‘z loyihalarim: yettita UzExam ilovasi, UzExam web '
                      'platformasi va EduStats.'),
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
            ('Жахонгир Кузибоев (Jayson Khan) — Mobile Developer в Consort Group и основатель UzExam. '
             'Flutter-приложения, Django-платформы и EduStats.')
        ),
        "eyebrow": "Обо мне · AI · Mobile · Full-stack · Ташкент",
        "h1": "Жахонгир Кузибоев",
        "h1_em": "(Jayson Khan)",
        "lede": (
            ('Mobile Developer в Consort Group: работаю над AI-интеграциями и картами в Growz и Bizon. Основал '
             'UzExam, где развиваю семь Flutter-приложений и платформу на Django. Также создал EduStats.')
        ),
        "sections": [
            {
                "h2": 'Опыт работы и образование',
                "body": ['С июня 2026 года работаю Mobile Developer в Consort Group над Flutter-приложениями Growz и Bizon. '
                         'Сейчас занимаюсь интеграцией AI и развитием функций карты в обоих продуктах.',
                         'С января по апрель 2026 года разрабатывал TaxPay в Soliq servis AJ на Flutter с Clean Architecture '
                         'и BLoC. Реализовал привязку карт, OTP, платежи и историю транзакций. Приложение было готово к '
                         'запуску, но после закрытия отдела не вышло в публичный доступ.',
                         'С сентября 2023 по декабрь 2025 года работал в UIC Group: разрабатывал Flutter-приложения для '
                         'Android и iOS, интегрировал API и улучшал производительность. В этот период также работал над AI '
                         'Business Assistant (август–ноябрь 2025): создавал функции ассистента и координировал мобильные '
                         'задачи.',
                         'В 2026 году окончил Ташкентский университет информационных технологий по направлению «Программная '
                         'инженерия», степень бакалавра. Сейчас работаю с Flutter-клиентами, Django API, PostgreSQL и Redis, '
                         'а также развиваю и поддерживаю собственные продукты.'],
            },
            {
                "h2": "Что я строю",
                "body": [
                    "UzExam — 85k+ опубликованных вопросов, 21k+ зарегистрированных пользователей и 7 мобильных"
                    " приложений: IELTS, Multilevel, SAT, DTM, национальный сертификат, автотест и интервью.",
                    "EduStats — 53k+ пользователей Telegram, 193 активных вуза в каталоге и проходные баллы для"
                    " 121 вуза. Отзывы студентов, рейтинги и статистика образования с указанием источников.",
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
                "a": ('Mobile Developer в Consort Group в Ташкенте и основатель UzExam. Также создал EduStats. Жахонгир '
                      'Кузибоев и Jayson Khan — один человек.'),
            },
            {
                "q": "Жахонгир Кузибоев и Jayson Khan — один человек?",
                "a": "Да. Jayson Khan — мой бренд в интернете; имя по паспорту — Jahongir Qo'ziboyev, "
                     "по-русски Жахонгир Кузибоев, узбекской кириллицей Жаҳонгир Қўзибоев.",
            },
            {
                "q": "Какой он разработчик?",
                "a": ('Разрабатываю приложения для Android и iOS на Flutter и бэкенд-сервисы на Python и Django. Сейчас '
                      'работаю с AI-интеграциями, картами, подготовкой к экзаменам и образовательными данными.'),
            },
            {
                "q": "Какие приложения он сделал?",
                "a": ('Growz и Bizon в Consort Group, TaxPay в Soliq servis AJ, корпоративные Flutter-приложения и AI '
                      'Business Assistant в UIC Group. Собственные проекты: семь приложений UzExam, веб-платформа UzExam '
                      'и EduStats.'),
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
            ('Jahongir Qo’ziboyev (Jayson Khan), Mobile Developer at Consort Group and founder of UzExam. '
             'Flutter apps, Django platforms and EduStats.')
        ),
        "eyebrow": "About · AI · Mobile · Full-stack · Tashkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            ('Mobile Developer at Consort Group, working on AI integrations and maps in Growz and Bizon. I '
             'founded UzExam, where I develop seven Flutter apps and the Django platform, and created EduStats.')
        ),
        "sections": [
            {
                "h2": 'Work and education',
                "body": ['Since June 2026, I have worked as a Mobile Developer at Consort Group on Growz and Bizon. My '
                         'current focus is AI integration and map features in both Flutter applications.',
                         'From January to April 2026, I built TaxPay at Soliq servis AJ with Flutter, Clean Architecture and '
                         'BLoC. I implemented card binding, OTP verification, payments and transaction history. The app '
                         'reached a production-ready stage but was not publicly released after the department closed.',
                         'I worked at UIC Group from September 2023 to December 2025, building Android and iOS applications '
                         'with Flutter, integrating APIs and improving app performance. During this period I also worked on '
                         'AI Business Assistant (August–November 2025), developing assistant features and coordinating '
                         'mobile tasks.',
                         'I graduated from Tashkent University of Information Technologies in 2026 with a bachelor’s degree '
                         'in Software Engineering. My work now spans Flutter clients, Django APIs, PostgreSQL, Redis and the '
                         'day-to-day maintenance of my own products.'],
            },
            {
                "h2": "What I build",
                "body": [
                    "UzExam — 85k+ published questions, 21k+ registered users and 7 mobile apps: IELTS, "
                    "Multilevel, SAT, DTM, national certification, driving tests and interviews.",
                    "EduStats — 53k+ Telegram users, 193 active university listings and admission scores for "
                    "121 universities. Student reviews, rankings and source-backed education statistics.",
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
                "a": ('Mobile Developer at Consort Group in Tashkent and founder of UzExam. I also created EduStats. '
                      'Jahongir Qo’ziboyev and Jayson Khan are the same person.'),
            },
            {
                "q": "Are Jahongir Qo'ziboyev and Jayson Khan the same person?",
                "a": "Yes. Jayson Khan is my online brand name; my legal name is Jahongir Qo'ziboyev — "
                     "Жаҳонгир Қўзибоев in Uzbek Cyrillic, Жахонгир Кузибоев in Russian.",
            },
            {
                "q": "What kind of developer is he?",
                "a": ('I build Android and iOS applications with Flutter and backend services with Python and Django. My '
                      'current work includes AI integrations, maps, exam practice and education data.'),
            },
            {
                "q": "Which apps has he built?",
                "a": ('Growz and Bizon at Consort Group; TaxPay at Soliq servis AJ; corporate Flutter apps and AI '
                      'Business Assistant at UIC Group. My own projects include seven UzExam apps, the UzExam web '
                      'platform and EduStats.'),
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
