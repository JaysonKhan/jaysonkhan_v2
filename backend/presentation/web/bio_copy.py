"""Code-owned bio-page copy in all four locales (xo, uz, ru, en).

Why a Python dict and not SiteSettings/`{% trans %}`:
  • This page is an SEO asset, not editorial content — it must stay stable and
    reviewable in git diffs, and it must never be half-overwritten by a seeder.
  • Storing it in SiteSettings would mean ~20 new translated columns + a
    migration + an admin tab for a single page. Storing it in django.po would
    scatter one page's prose across four .po files.

Target queries this page exists to answer (all four scripts):
    Jahongir Qo'ziboyev · Qo'ziboyev Jahongir · Жаҳонгир Қўзибоев ·
    Жахонгир Кузибоев · Jayson Khan · Voice AI Engineer · ovozli AI ·
    AI dasturchi · AI разработчик · голосовой AI · AI engineer
    (role wording switched to Voice AI Engineer on 2026-11-18, owner's request)

EVERY factual claim here is sourced from copy already shipped in
`ops/management/commands/apply_edtech_founder_copy.py` (2026-07 resume +
UzExam PTA-2026 docs). Product counts were refreshed on 2026-09-21 from
read-only production aggregates; see docs/archive/project-facts-2026-09.md.

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
    ("Voice AI", "Real-time audio streaming · WebSockets · Socket.IO · PCM audio · turn-taking · echo prevention"),
    ("AI", "LLM APIs (Claude, Gemini, OpenAI) · AI pipelines · vision-model checks · Claude Code"),
    ("Backend", "Python · Django · DRF · FastAPI · aiogram · PostgreSQL · Redis"),
    ("Mobile clients", "Flutter · Kotlin · iOS · Android"),
    ("Web / DevOps", "JavaScript · TypeScript · HTMX · Nginx · Linux · CI/CD"),
]

BIO = {
    # ── XO — Khorezm dialect, owner's signature voice ────────────────────
    "xo": {
        "seo_title": "Jahongir Qo'ziboyev (Jayson Khan) — Voice AI Engineer",
        "meta_description": (
            "Jahongir Qo'ziboyev (Jayson Khan) — Xorazmdan chiqqan Voice AI Engineer, UzExam va"
            " EduStats asoschisi. 25+ ilova, 167k+ savol."
        ),
        "eyebrow": "Kim u? · Voice AI Engineer · Toshkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            "Man Jahongir Qo'ziboyev — internetda Jayson Khan nomi bilan tanilganman. "
            "Xorazmdan chiqqanman, Toshkentda ishlayman. Mobil dasturchi bo'lib boshlab, "
            "3+ yilda 25+ ilova yetkazganman; endi Voice AI Engineer va EdTech founder sifatida "
            "24/7 AI-agentla bilan test platformala, ta'lim analitikasi va AI mentorla quraman."
        ),
        "sections": [
            {
                "h2": "Mobil dasturchilikdan Voice AI'gacha",
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
                    "Bugun Consort Group'da Voice AI Engineer'man: Growz'dagi real vaqtli ovozli AI "
                    "agronomni qurdim — oqimli audio, navbat bilan gaplashish, aks-sadoni bostirish.",
                    "Full-stack tomoni ham manda: mobil oldingi tajriba ustiga Python/Django backend, "
                    "PostgreSQL, Nginx va Linux server boshqaruvi qo'shildi. Kod, QA, monitoring va "
                    "tungi incident-response — 24/7 AI-agentlada; strategiya, kontent sifati va "
                    "mas'uliyat — manda.",
                ],
            },
            {
                "h2": "Nima quraman",
                "body": [
                    "UzExam (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi. 3 "
                    "oyda yolg'iz qurilgan: 7 mobil ilova, 39k+ ro'yxatdan o'tgan foydalanuvchi, 167k+ "
                    "ochiq savol, imtihon yo‘nalishla (DTM, IELTS, SAT, Avtotest va boshqala), "
                    "takrorlanmas savolla (Uniqueness Engine), SM-2 takrorlash, antifraud reyting, B2B "
                    "tenant tizimi va Click/Stars to'lovla.",
                    "EduStats (edustats.uz) — talabalar fikri va ta'lim analitikasi platformasi: "
                    "universitetla reytingi, 54k+ Telegram auditoriyasi va 126 OTM o'tish"
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
                "a": "Jahongir Qo'ziboyev (Jayson Khan) — O'zbekistonda ishlaydigan Voice AI "
                     "Engineer, UzExam va EduStats asoschisi. Xorazmdan, Toshkentda "
                     "yashaydi. President Tech Award 2026 ishtirokchisi.",
            },
            {
                "q": "Jahongir Qo'ziboyev va Jayson Khan bir odammi?",
                "a": "Ha. Jayson Khan — internetdagi brend nomim; pasportdagi ismim Jahongir "
                     "Qo'ziboyev. Kirilda Жаҳонгир Қўзибоев, ruschada Жахонгир Кузибоев deb yoziladi.",
            },
            {
                "q": "Qanaqa dasturchi?",
                "a": "Voice AI Engineer: real vaqtda ishlaydigan ovozli AI yordamchila quraman — "
                     "WebSocket, oqimli audio, LLM API. Backend tomondan Python/Django, mobil "
                     "tomondan Flutter (25+ ilova).",
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
        "cta_text": "Ovozli AI yordamchi, AI mahsulot yo EdTech platforma — brifni tashlang, qolganini surishtiraman.",
        "cta_btn": "Bog'lanish",
    },

    # ── UZ — standard Latin Uzbek ────────────────────────────────────────
    "uz": {
        "seo_title": "Jahongir Qo'ziboyev (Jayson Khan) — Voice AI Engineer",
        "meta_description": (
            ('Jahongir Qo‘ziboyev (Jayson Khan) — Consort Group’da Voice AI Engineer va UzExam asoschisi. Real '
             'vaqtda ishlaydigan ovozli AI yordamchilar va LLM.')
        ),
        "eyebrow": "Men haqimda · Voice AI Engineer · Toshkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            ('Consort Group’da Voice AI Engineer sifatida Growz ilovasining real vaqtda ishlaydigan ovozli AI '
             'agronomini qurganman. UzExam asoschisiman: Django platformasi, yettita mobil ilova va LLM asosidagi '
             'AI quvurlarini rivojlantiraman. EduStats ham o‘z loyiham.')
        ),
        "sections": [
            {
                "h2": 'Ish tajribasi va ta’lim',
                "body": ['2026-yil iyunidan Consort Group’da Voice AI Engineer bo‘lib ishlayman. Growz’dagi ovozli AI '
                         'agronomni qurdim: Socket.IO orqali real vaqtdagi ovozli suhbat, oqimli PCM audio, navbat bilan '
                         'gaplashish, aks-sadoni bostirish va audio fokusni boshqarish. Bizon’da oqimli AI-chatni, '
                         'Growz’da rasm orqali tashxisni ham chiqardim.',
                         '2026-yil yanvar–aprel oylarida Soliq servis AJ’da Software Engineer sifatida TaxPay’ni Flutter, '
                         'Clean Architecture va BLoC '
                         'asosida qurdim. Karta ulash, OTP, to‘lovlar va tranzaksiyalar tarixini ishlab chiqdim. Ilova ishga '
                         'tushirishga tayyor holatga yetdi, ammo bo‘lim yopilgach ommaga chiqarilmadi.',
                         '2023-yil sentabridan 2025-yil dekabrigacha UIC Group’da Software Engineer sifatida Android va iOS '
                         'ilovalari, API integratsiyalari va ilova unumdorligi ustida ishladim. Shu davrda AI Business Assistant '
                         'loyihasida ham (2025-yil avgust–noyabr) assistent funksiyalarini ishlab chiqdim va mobil jamoa '
                         'vazifalarini muvofiqlashtirdim.',
                         '2026-yilda Toshkent axborot texnologiyalari universitetining Dasturiy injiniring yo‘nalishini '
                         'bakalavr darajasi bilan tamomladim. Hozirgi ishlarim ovozli AI, LLM integratsiyalari, Django API, '
                         'PostgreSQL, Redis va o‘z mahsulotlarimni doimiy rivojlantirishni qamrab oladi.'],
            },
            {
                "h2": "Nima quraman",
                "body": [
                    "UzExam — 167k+ ochiq savol, 39k+ ro'yxatdan o'tgan foydalanuvchi va 7 mobil ilova. IELTS, "
                    "Multilevel, SAT, DTM, Milliy sertifikat, Avtotest va Intervyu — web, Telegram va "
                    "Flutter'da.",
                    "EduStats — 54k+ Telegram foydalanuvchi, katalogda 208 faol OTM va 126 OTM bo'yicha o'tish "
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
                "a": ('Toshkentda Consort Group’da ishlaydigan Voice AI Engineer va UzExam asoschisi. EduStats’ni ham '
                      'yaratganman. Jahongir Qo‘ziboyev va Jayson Khan — bir inson.'),
            },
            {
                "q": "Jahongir Qo'ziboyev va Jayson Khan bir odammi?",
                "a": "Ha. Jayson Khan — internetdagi brend nomim; pasportdagi ismim Jahongir "
                     "Qo'ziboyev. Kirilda Жаҳонгир Қўзибоев, ruschada Жахонгир Кузибоев deb yoziladi.",
            },
            {
                "q": "U qanday dasturchi?",
                "a": ('Voice AI Engineer: odamlar ovoz bilan gaplashadigan, real vaqtda ishlaydigan AI yordamchilarni '
                      'quraman (WebSocket, oqimli audio, LLM API). Backend — Python va Django, mobil mijozlar — Flutter '
                      'va Kotlin.'),
            },
            {
                "q": "Qaysi ilovalarni qurgan?",
                "a": ('Consort Group’da Growz’ning ovozli AI agronomi va Bizon AI-chati, Soliq servis AJ’da TaxPay, '
                      'UIC Group’da korporativ ilovalar va AI Business Assistant. O‘z loyihalarim: yettita UzExam ilovasi, UzExam web '
                      'platformasi va EduStats.'),
            },
            {
                "q": "Qanday bog'lanish mumkin?",
                "a": "jaysonkhan.com kontakt sahifasi yoki Telegram (@jaysonkhan) orqali — Telegram "
                     "eng tez javob beradigan kanal.",
            },
        ],
        "cta_title": "Loyihangiz bormi?",
        "cta_text": "Ovozli AI yordamchi, AI mahsulot yoki EdTech platforma — brifni tashlang, qolganini o'zim aniqlayman.",
        "cta_btn": "Bog'lanish",
    },

    # ── RU ───────────────────────────────────────────────────────────────
    "ru": {
        "seo_title": "Жахонгир Кузибоев (Jayson Khan) — Voice AI Engineer",
        "meta_description": (
            ('Жахонгир Кузибоев (Jayson Khan) — Voice AI Engineer в Consort Group и основатель UzExam. Голосовые '
             'AI-ассистенты в реальном времени, LLM и Django-платформы.')
        ),
        "eyebrow": "Обо мне · Voice AI Engineer · Ташкент",
        "h1": "Жахонгир Кузибоев",
        "h1_em": "(Jayson Khan)",
        "lede": (
            ('Voice AI Engineer в Consort Group: разработал голосового AI-агронома в Growz — живой голосовой '
             'диалог в реальном времени. Основал UzExam: платформа на Django, семь мобильных приложений и '
             'AI-конвейеры на LLM. Также создал EduStats.')
        ),
        "sections": [
            {
                "h2": 'Опыт работы и образование',
                "body": ['С июня 2026 года работаю Voice AI Engineer в Consort Group. Разработал голосового AI-агронома в '
                         'Growz: голосовой диалог в реальном времени через Socket.IO, потоковое PCM-аудио, очередность '
                         'реплик, подавление эха и управление аудиофокусом. Также выпустил потоковый AI-чат в Bizon и '
                         'диагностику растений по фото в Growz.',
                         'С января по апрель 2026 года работал Software Engineer в Soliq servis AJ: разрабатывал TaxPay на '
                         'Flutter с Clean Architecture '
                         'и BLoC. Реализовал привязку карт, OTP, платежи и историю транзакций. Приложение было готово к '
                         'запуску, но после закрытия отдела не вышло в публичный доступ.',
                         'С сентября 2023 по декабрь 2025 года работал Software Engineer в UIC Group: разрабатывал '
                         'приложения для Android и iOS, интегрировал API и улучшал производительность. В этот период также работал над AI '
                         'Business Assistant (август–ноябрь 2025): создавал функции ассистента и координировал мобильные '
                         'задачи.',
                         'В 2026 году окончил Ташкентский университет информационных технологий по направлению «Программная '
                         'инженерия», степень бакалавра. Сейчас работаю с голосовым AI, LLM-интеграциями, Django API, '
                         'PostgreSQL и Redis, а также развиваю и поддерживаю собственные продукты.'],
            },
            {
                "h2": "Что я строю",
                "body": [
                    "UzExam — 167k+ опубликованных вопросов, 39k+ зарегистрированных пользователей и 7 мобильных"
                    " приложений: IELTS, Multilevel, SAT, DTM, национальный сертификат, автотест и интервью.",
                    "EduStats — 54k+ пользователей Telegram, 208 активных вузов в каталоге и проходные баллы для"
                    " 126 вузов. Отзывы студентов, рейтинги и статистика образования с указанием источников.",
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
                "a": ('Voice AI Engineer в Consort Group в Ташкенте и основатель UzExam. Также создал EduStats. Жахонгир '
                      'Кузибоев и Jayson Khan — один человек.'),
            },
            {
                "q": "Жахонгир Кузибоев и Jayson Khan — один человек?",
                "a": "Да. Jayson Khan — мой бренд в интернете; имя по паспорту — Jahongir Qo'ziboyev, "
                     "по-русски Жахонгир Кузибоев, узбекской кириллицей Жаҳонгир Қўзибоев.",
            },
            {
                "q": "Какой он разработчик?",
                "a": ('Voice AI Engineer: создаю голосовых AI-ассистентов, с которыми разговаривают в реальном времени '
                      '(WebSockets, потоковое аудио, API LLM). Бэкенд — Python и Django, мобильные клиенты — Flutter '
                      'и Kotlin.'),
            },
            {
                "q": "Какие приложения он сделал?",
                "a": ('Голосовой AI-агроном в Growz и AI-чат в Bizon (Consort Group), TaxPay в Soliq servis AJ, '
                      'корпоративные приложения и AI Business Assistant в UIC Group. Собственные проекты: семь приложений UzExam, веб-платформа UzExam '
                      'и EduStats.'),
            },
            {
                "q": "Как с ним связаться?",
                "a": "Через страницу контактов на jaysonkhan.com или в Telegram (@jaysonkhan) — "
                     "Telegram отвечает быстрее всего.",
            },
        ],
        "cta_title": "Есть проект?",
        "cta_text": "Голосовой AI-ассистент, AI-продукт или EdTech-платформа — пришлите бриф, остальное уточню сам.",
        "cta_btn": "Связаться",
    },

    # ── EN ───────────────────────────────────────────────────────────────
    "en": {
        "seo_title": "Jahongir Qo'ziboyev (Jayson Khan) — Voice AI Engineer",
        "meta_description": (
            ('Jahongir Qo’ziboyev (Jayson Khan), Voice AI Engineer at Consort Group and founder of UzExam. '
             'Real-time AI voice assistants, LLM pipelines and Django platforms.')
        ),
        "eyebrow": "About · Voice AI Engineer · Tashkent",
        "h1": "Jahongir Qo'ziboyev",
        "h1_em": "(Jayson Khan)",
        "lede": (
            ('Voice AI Engineer at Consort Group: I built the real-time voice AI agronomist in Growz. I founded '
             'UzExam, where I develop the Django platform, seven mobile apps and LLM-based AI pipelines, and '
             'created EduStats.')
        ),
        "sections": [
            {
                "h2": 'Work and education',
                "body": ['Since June 2026, I have worked as a Voice AI Engineer at Consort Group. I built the voice AI '
                         'agronomist in Growz: a real-time voice conversation over Socket.IO with streamed PCM audio, '
                         'turn-taking, echo prevention and audio-focus handling. I also delivered the streaming AI chat in '
                         'Bizon and photo-based crop diagnosis in Growz.',
                         'From January to April 2026, as a Software Engineer at Soliq servis AJ, I built TaxPay with '
                         'Flutter, Clean Architecture and '
                         'BLoC. I implemented card binding, OTP verification, payments and transaction history. The app '
                         'reached a production-ready stage but was not publicly released after the department closed.',
                         'I worked as a Software Engineer at UIC Group from September 2023 to December 2025, building '
                         'Android and iOS applications, integrating APIs and improving app performance. During this period I also worked on '
                         'AI Business Assistant (August–November 2025), developing assistant features and coordinating '
                         'mobile tasks.',
                         'I graduated from Tashkent University of Information Technologies in 2026 with a bachelor’s degree '
                         'in Software Engineering. My work now spans voice AI, LLM integrations, Django APIs, PostgreSQL, '
                         'Redis and the day-to-day maintenance of my own products.'],
            },
            {
                "h2": "What I build",
                "body": [
                    "UzExam — 167k+ published questions, 39k+ registered users and 7 mobile apps: IELTS, "
                    "Multilevel, SAT, DTM, national certification, driving tests and interviews.",
                    "EduStats — 54k+ Telegram users, 208 active university listings and admission scores for "
                    "126 universities. Student reviews, rankings and source-backed education statistics.",
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
                "a": ('Voice AI Engineer at Consort Group in Tashkent and founder of UzExam. I also created EduStats. '
                      'Jahongir Qo’ziboyev and Jayson Khan are the same person.'),
            },
            {
                "q": "Are Jahongir Qo'ziboyev and Jayson Khan the same person?",
                "a": "Yes. Jayson Khan is my online brand name; my legal name is Jahongir Qo'ziboyev — "
                     "Жаҳонгир Қўзибоев in Uzbek Cyrillic, Жахонгир Кузибоев in Russian.",
            },
            {
                "q": "What kind of developer is he?",
                "a": ('A Voice AI Engineer: I build real-time AI assistants that people talk to (WebSockets, streamed '
                      'audio, LLM APIs). Backend in Python and Django, mobile clients in Flutter and Kotlin.'),
            },
            {
                "q": "Which apps has he built?",
                "a": ('The voice AI agronomist in Growz and the AI chat in Bizon at Consort Group; TaxPay at Soliq '
                      'servis AJ; corporate apps and AI Business Assistant at UIC Group. My own projects include seven UzExam apps, the UzExam web '
                      'platform and EduStats.'),
            },
            {
                "q": "How can I contact him?",
                "a": "Through the contact page on jaysonkhan.com or via Telegram (@jaysonkhan) — "
                     "Telegram is the fastest channel.",
            },
        ],
        "cta_title": "Got a project?",
        "cta_text": "A voice AI assistant, an AI product or an EdTech platform — send the brief, I'll take it from there.",
        "cta_btn": "Get in touch",
    },
}


def get_bio(lang_code: str) -> dict:
    """Return the bio block for `lang_code`, falling back to the xo default."""
    return BIO.get(lang_code) or BIO["xo"]
