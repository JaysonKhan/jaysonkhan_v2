"""Backfill SiteSettings translations: Khorezm dialect (xo), Standard Uzbek (uz),
Russian (ru), English (en).

Strategy:
- Existing values currently live in `_xo` columns (modeltranslation default).
  Most of them are English (legacy from before i18n was added).
- This migration writes proper translations to all 4 columns:
    field_xo  → Khorezm-flavored Uzbek (slightly more colloquial)
    field_uz  → Standard literary Uzbek (Latin)
    field_ru  → Russian
    field_en  → English (current copy moves here)

Idempotent: skips rows where target column is already non-empty AND not equal
to the legacy default. Admin custom edits are preserved.
"""
from django.db import migrations


T = {  # field_name → {lang: translation}
    'site_title': {
        'xo': "Jaysonkhan · VibeCoder Studyosi",
        'uz': "Jaysonkhan · VibeCoder Studiyasi",
        'ru': "Jaysonkhan · Студия VibeCoder",
        'en': "Jaysonkhan · VibeCoder Build Studio",
    },
    'site_tagline': {
        'xo': "VibeCoder — AI yordamida web ilovalar va Telegram botlar yasab beramiz.",
        'uz': "VibeCoder — AI-yordamlashgan rivojlanish bilan web ilovalar va Telegram botlar.",
        'ru': "VibeCoder — продакшн веб-приложения и Telegram-боты с AI-инструментами.",
        'en': "VibeCoder — shipping production web apps & Telegram bots via AI-augmented development.",
    },
    'meta_description': {
        'xo': "Jaysonkhan — Toshkentdagi VibeCoder. AI yordamida web ilovalar, Telegram botlar va to'liq tizimlar yasaymiz.",
        'uz': "Jaysonkhan — Toshkentdagi VibeCoder. AI-yordamlashgan rivojlanish bilan web ilovalar va Telegram botlar.",
        'ru': "Jaysonkhan — VibeCoder из Ташкента. AI-augmented разработка веб-приложений и Telegram-ботов.",
        'en': "Jaysonkhan — VibeCoder shipping production web apps & Telegram bots via AI-augmented development. Build Studio · Tashkent.",
    },
    'meta_keywords': {
        'xo': "VibeCoder, Django, Python, Telegram bot, AI, Claude Code, Toshkent",
        'uz': "VibeCoder, Django, Python, Telegram bot, AI, Claude Code, full-stack, Toshkent",
        'ru': "VibeCoder, Django, Python, Telegram-боты, AI разработка, Claude Code, Ташкент",
        'en': "VibeCoder, Django, Python, Telegram bots, AI development, Claude Code, full stack, Tashkent",
    },
    'nav_cta_text': {
        'xo': "Aloqa",
        'uz': "Bog'lanish",
        'ru': "Связаться",
        'en': "Contact",
    },
    'hero_title': {
        'xo': "Web ilovalar va Telegram botlar yasaymiz.",
        'uz': "Web ilovalar va Telegram botlarni ishga tushiraman.",
        'ru': "Создаю production веб-приложения и Telegram-ботов.",
        'en': "I ship production web apps and Telegram bots.",
    },
    'hero_subtitle': {
        'xo': "VibeCoder — Django bilan kuchli web ilovalar, Aiogram bilan Telegram botlar va Claude Code bilan AI tezlikda yasayman. Tez ishlanadi, mahkam turadi.",
        'uz': "VibeCoder — Django asosida web ilovalar, Aiogram asosida Telegram botlar va AI yordamchi bilan tezroq yetkazib beraman. Tez quriladi, mustahkam ishlaydi.",
        'ru': "VibeCoder — создаю production веб-приложения, Telegram-ботов и AI-системы. Быстро строим с Claude Code, надёжно с Django.",
        'en': "VibeCoder specializing in shipping production-grade web applications, Telegram bots, and AI-augmented systems. Built fast with Claude Code, built to last with Django.",
    },
    'about_title': {
        'xo': "Men haqimda",
        'uz': "Men haqimda",
        'ru': "Обо мне",
        'en': "About",
    },
    'about_description': {
        'xo': "3+ yillik tajribaga ega VibeCoder. Django bilan web ilovalar, Aiogram bilan Telegram botlar yasayman. Tailwind dizayn tizimida ishlayman — hammasi Claude Code yordami va sog'lom workflow bilan. Mobile da Flutter, Android, iOS bilan boshlaganman, endi web + bot + AI ga o'tdim.",
        'uz': "3+ yil tajribaga ega full-stack VibeCoder. Django bilan production web ilovalar, Aiogram bilan Telegram botlar va Tailwind bilan dizayn tizimlari yarataman — hammasi Claude Code yordami va izchil workflow bilan. Avval mobile (Flutter, Android, iOS) yo'nalishida ishlaganman, hozir studio diqqati web + bot + AI ga ko'chgan.",
        'ru': "Full-stack VibeCoder с 3+ летним опытом разработки production-систем. Создаю веб-приложения на Django, Telegram-ботов на Aiogram и дизайн-системы на Tailwind — всё дополнено Claude Code и продуманным workflow. Раньше работал в мобайле (Flutter, Android, iOS), но центр тяжести студии переместился на веб + боты + AI.",
        'en': "Full-stack VibeCoder with 3+ years shipping production systems. I build web apps with Django, Telegram bots with Aiogram, and design systems with Tailwind — all augmented by Claude Code and a sane workflow. Background in mobile (Flutter, Android, iOS), but the studio's center of gravity has moved to web + bots + AI.",
    },
    'stat_1_label': {
        'xo': "Yil tajriba",
        'uz': "Yil tajriba",
        'ru': "Лет опыта",
        'en': "Years Experience",
    },
    'stat_2_label': {
        'xo': "Loyiha yetkazilgan",
        'uz': "Yetkazib berilgan loyihalar",
        'ru': "Запущенных проектов",
        'en': "Apps Delivered",
    },
    'stat_3_label': {
        'xo': "Yuklab olingan",
        'uz': "Yuklab olishlar",
        'ru': "Загрузок",
        'en': "App Downloads",
    },
    'stat_4_label': {
        'xo': "Toza arxitektura",
        'uz': "Clean Architecture",
        'ru': "Чистая архитектура",
        'en': "Clean Architecture",
    },
    'featured_projects_title': {
        'xo': "Tanlangan loyihalar",
        'uz': "Tanlangan loyihalar",
        'ru': "Избранные проекты",
        'en': "Featured Apps",
    },
    'projects_page_title': {
        'xo': "Loyihalar",
        'uz': "Loyihalar",
        'ru': "Проекты",
        'en': "Work",
    },
    'projects_page_subtitle': {
        'xo': "Yasagan va productionga chiqargan ishlarim. Real foydalanuvchilar, real telemetriya, real tashriflar.",
        'uz': "Yaratilgan va ishga tushirilgan loyihalar — real foydalanuvchilar, haqiqiy telemetriya bilan.",
        'ru': "Реальные production-проекты — настоящие пользователи, телеметрия и App Store отзывы.",
        'en': "Every entry is a real production app — paying users, telemetry I check on Mondays.",
    },
    'blog_page_title': {
        'xo': "Yozuvlar",
        'uz': "Jurnal",
        'ru': "Журнал",
        'en': "Journal",
    },
    'blog_page_subtitle': {
        'xo': "AI-yordamlashgan dasturlash, full-stack yetkazib berish va real ishlab turgan tizimlar haqida yozuvlar.",
        'uz': "AI-yordamchi rivojlanish, full-stack yetkazib berish va haqiqiy production tizimlari haqidagi qaydlar.",
        'ru': "Заметки об AI-augmented разработке, full-stack доставке и production-системах, которые реально работают.",
        'en': "Notes on AI-augmented development, full-stack delivery, and shipping production systems that actually run.",
    },
    'contact_page_title': {
        'xo': "Aloqa",
        'uz': "Aloqa",
        'ru': "Контакт",
        'en': "Contact",
    },
    'contact_page_subtitle': {
        'xo': "Web ilova, Telegram bot yoki AI tizim qilmoqchimisiz? Birga yasaymiz.",
        'uz': "Web ilova, Telegram bot yoki AI-tizim quryapsizmi? Birgalikda ishga tushiramiz.",
        'ru': "Делаете веб-приложение, Telegram-бота или AI-систему? Запустим вместе.",
        'en': "Building a web app, Telegram bot, or AI-augmented system? Let's ship it together.",
    },
    'resume_button_text': {
        'xo': "CV yuklash",
        'uz': "CV yuklab olish",
        'ru': "Скачать CV",
        'en': "Download CV",
    },
    'footer_description': {
        'xo': "Production-darajadagi web ilovalar va Telegram botlar yaratuvchi kichik studyo.",
        'uz': "Production-darajadagi web ilovalar, Telegram botlar va AI-tizimlar yaratuvchi kichik studio.",
        'ru': "Маленькая студия, создающая production веб-приложения, Telegram-боты и AI-системы.",
        'en': "A small studio engineering production-grade web apps, Telegram bots, and AI-augmented systems.",
    },
    'footer_text': {
        'xo': "© 2026 Jaysonkhan Studyo · Toshkent · Barcha huquqlar himoyalangan",
        'uz': "© 2026 Jaysonkhan Studio · Toshkent, UZ · Barcha huquqlar himoyalangan",
        'ru': "© 2026 Jaysonkhan Studio · Ташкент, UZ · Все права защищены",
        'en': "© 2026 Jaysonkhan Studio · Tashkent, UZ · All rights reserved",
    },

    # ── Editorial v3 ────────────────────────────────────────────────────────
    'hero_eyebrow': {
        'xo': "Shaxsiy · Build Studyo · VibeCoder",
        'uz': "Shaxsiy · Build Studio · VibeCoder",
        'ru': "Личный · Build Studio · VibeCoder",
        'en': "Personal · Build Studio · VibeCoder",
    },
    'brand_tagline': {
        'xo': "Build Studyo · 2022 yildan",
        'uz': "Build Studio · 2022-dan",
        'ru': "Build Studio · С 2022",
        'en': "Build Studio · Est. 2022",
    },
    'manifesto_eyebrow': {
        'xo': "02 — Falsafa",
        'uz': "02 — Falsafa",
        'ru': "02 — Философия",
        'en': "02 — Philosophy",
    },
    'manifesto_title': {
        'xo': "Manifest.",
        'uz': "Manifesto.",
        'ru': "Манифест.",
        'en': "Manifesto.",
    },
    'manifesto_label': {
        'xo': "03 PRINSIP · YASAYISH HAQIDA",
        'uz': "03 PRINSIP · QURISH HAQIDA",
        'ru': "03 ПРИНЦИПА · О СТРОИТЕЛЬСТВЕ",
        'en': "03 PRINCIPLES · ON BUILDING",
    },
    'metrics_eyebrow': {
        'xo': "03 — Sonlar bilan",
        'uz': "03 — Raqamlar bo'yicha",
        'ru': "03 — В цифрах",
        'en': "03 — By the numbers",
    },
    'metrics_title': {
        'xo': 'Tarixiy yozuv,<br><em style="font-weight: 400;">o\'lchangan.</em>',
        'uz': 'Yo\'l qaydnomasi,<br><em style="font-weight: 400;">o\'lchangan.</em>',
        'ru': 'Послужной список,<br><em style="font-weight: 400;">в цифрах.</em>',
        'en': 'A track record,<br><em style="font-weight: 400;">measured.</em>',
    },
    'metrics_description': {
        'xo': "Oxirgi to'rt yildagi production loyihalardan olingan raqamlar. Pitch deck emas — har kuni ko'radigan dashboardlardan.",
        'uz': "Oxirgi to'rt yildagi production loyihalardan olingan raqamlar. Pitch deck'dan emas, har kuni ko'rib turadigan dashboardlardan.",
        'ru': "Цифры из реальных production-проектов за последние четыре года. Не из питч-дека — из дашбордов, которые я проверяю каждое утро.",
        'en': "Numbers from live production apps over the last four years. Pulled from dashboards, not pitch decks.",
    },
    'process_eyebrow': {
        'xo': "05 — Qanday ishlayman",
        'uz': "05 — Qanday ishlayman",
        'ru': "05 — Как я работаю",
        'en': "05 — How I work",
    },
    'process_title': {
        'xo': 'Besh bosqich,<br><em style="font-weight: 400;">syurprizsiz.</em>',
        'uz': 'Besh qadam,<br><em style="font-weight: 400;">kutilmagansiz.</em>',
        'ru': 'Пять шагов,<br><em style="font-weight: 400;">без сюрпризов.</em>',
        'en': 'Five steps,<br><em style="font-weight: 400;">no surprises.</em>',
    },
    'cta_eyebrow': {
        'xo': "07 — Ochiq kanal",
        'uz': "07 — Ochiq kanal",
        'ru': "07 — Открытый канал",
        'en': "07 — Open channel",
    },
    'cta_title_pre': {
        'xo': "Loyihangizni<br>olib keling.",
        'uz': "Loyihangizni<br>olib keling.",
        'ru': "Приносите<br>бриф.",
        'en': "Bring the<br>brief.",
    },
    'cta_title_em': {
        'xo': "Jamoa bilan men kelaman.",
        'uz': "Jamoa bilan men kelaman.",
        'ru': "Я приведу команду.",
        'en': "I'll bring the team.",
    },
    'cta_description': {
        'xo': "Q2 2026 da ikki bo'sh joy ochiladi. Eng mosi: ambitsiyali web ilovalar, Telegram bot mahsulotlari yoki AI tizimlar — 12+ haftalik runway va real foydalanuvchi bazasi bilan.",
        'uz': "Q2 2026 uchun ikki bo'sh slot ochilmoqda. Eng mosi: ambitsiyali web ilovalar, Telegram bot mahsulotlari yoki AI-tizimlar — 12+ haftalik runway va haqiqiy foydalanuvchi bazasi rejasi bilan.",
        'ru': "Открываются два слота на Q2 2026. Подходит: амбициозные веб-приложения, Telegram-бот продукты или AI-системы с runway 12+ недель и реальной аудиторией.",
        'en': "Two slots opening for Q2 2026. Best fit: ambitious web apps, Telegram bot products, or AI-augmented systems with a 12+ week runway and a real user base in mind.",
    },
    'cta_button_text': {
        'xo': "Suhbatni boshlash",
        'uz': "Suhbatni boshlash",
        'ru': "Начать разговор",
        'en': "Start a conversation",
    },
    'cta_response_label': {
        'xo': "O'rtacha javob · 4–6 soat",
        'uz': "O'rtacha javob · 4–6 soat",
        'ru': "Среднее время ответа · 4–6 ч",
        'en': "Avg. response · 4–6h",
    },
    'contact_form_label': {
        'xo': "Forma 7741",
        'uz': "Forma 7741",
        'ru': "Форма 7741",
        'en': "Brief / Form 7741",
    },
    'contact_form_title': {
        'xo': "Nima yasamoqchisiz, ayting.",
        'uz': "Nima qurmoqchisiz, ayting.",
        'ru': "Расскажите, что строите.",
        'en': "Tell me what you're building.",
    },
    'contact_availability_status': {
        'xo': "Bo'sh · Q2 2026",
        'uz': "Bo'sh · Q2 2026",
        'ru': "Доступен · Q2 2026",
        'en': "Available · Q2 2026",
    },
    'contact_availability_note': {
        'xo': "Ikki yo'nalish bo'sh. Toshkent, UTC+5.",
        'uz': "Ikki bo'sh slot mavjud. Toshkent, UTC+5.",
        'ru': "Открыты два слота. Ташкент, UTC+5.",
        'en': "Two engagement slots open. Tashkent, UTC+5.",
    },
    'team_hero_eyebrow': {
        'xo': "Studyo · Jamoa ro'yxati",
        'uz': "Studio · Jamoa",
        'ru': "Студия · Команда",
        'en': "Studio · Crew Manifest",
    },
    'team_hero_headline': {
        'xo': 'Har bir kuchli mahsulot ortida<br><em>diqqatli</em> jamoa turadi.',
        'uz': 'Har bir kuchli mahsulot ortida<br><em>diqqatli</em> jamoa turadi.',
        'ru': 'За каждым сильным продуктом стоит<br><em>сосредоточенная</em> команда.',
        'en': 'Behind every<br>strong product is a<br><em>focused</em> team.',
    },
    'team_intro': {
        'xo': "Full-stack quruvchilar, dizaynerlar va operatorlardan iborat kichik studyo. Production web ilovalar, Telegram botlar va AI tizimlarini yasaymiz — vazifaga mos asbob bilan.",
        'uz': "Full-stack quruvchilar, dizaynerlar va operatorlardan iborat kichik studio. Production web ilovalar, Telegram botlar va AI-tizimlar yaratamiz — vazifaga mos har qanday asbob bilan.",
        'ru': "Маленькая студия full-stack строителей, дизайнеров и операторов. Создаём production веб-приложения, Telegram-ботов и AI-системы — используя любой инструмент, подходящий для задачи.",
        'en': "A small studio of full-stack builders, designers, and operators. We ship production web apps, Telegram bots, and AI-augmented systems — using whatever tool fits the problem.",
    },
    'team_values_eyebrow': {
        'xo': "Ish prinsiplari",
        'uz': "Ish prinsiplari",
        'ru': "Принципы работы",
        'en': "Operating principles",
    },
    'team_values_title': {
        'xo': 'Qanday<br>fikr<br>yuritamiz.',
        'uz': 'Qanday<br>fikr<br>yuritamiz.',
        'ru': 'Как мы<br>думаем.',
        'en': 'How we<br>think.',
    },
    'team_values_intro': {
        'xo': "Olti qiymat, to'rt yil birga. Bular devordagi shiorlar emas — biz har safar tushadigan tanlovlardir.",
        'uz': "Olti qiymat, to'rt yil birga. Bular devordagi shiorlar emas — biz har safar qaytariladigan murosalardir.",
        'ru': "Шесть ценностей, четыре года вместе. Это не лозунги на стене — это компромиссы, к которым мы постоянно возвращаемся.",
        'en': "Six values, four years together. These aren't slogans on a wall — they're the trade-offs we keep landing on.",
    },
    'about_section_eyebrow': {
        'xo': "Men · Operator",
        'uz': "Men · Operator",
        'ru': "Обо мне · Оператор",
        'en': "About · Operator",
    },
    'footer_cta_eyebrow': {
        'xo': "Yakun / Uzatish tugadi",
        'uz': "Yakun / Uzatish tugadi",
        'ru': "Конец / Передача завершена",
        'en': "End / Transmission complete",
    },
    'footer_cta_headline': {
        'xo': 'Loyihangiz bormi?<br><em>Keling </em>kanalni ochaylik.',
        'uz': 'Loyihangiz bormi?<br><em>Keling </em>kanalni ochaylik.',
        'ru': 'Есть бриф?<br><em>Давайте </em>откроем канал.',
        'en': "Got a brief?<br><em>Let's </em>open a channel.",
    },
    'error_404_headline': {
        'xo': 'Bu sahifa<br><em style="font-weight: 400;">xaritadan chiqib ketganga o\'xshaydi.</em>',
        'uz': 'Bu sahifa<br><em style="font-weight: 400;">xaritadan chiqib ketgan.</em>',
        'ru': 'Эта страница<br><em style="font-weight: 400;">слетела с карты.</em>',
        'en': 'Looks like this page<br><em style="font-weight: 400;">drifted off the map.</em>',
    },
    'error_404_description': {
        'xo': "Qidirayotgan sahifa ko'chirilgan, arxivlangan yoki umuman bo'lmagan. Yo'lingizni qaytaramiz.",
        'uz': "Qidirayotgan sahifa ko'chirilgan, arxivlangan yoki umuman bo'lmagan bo'lishi mumkin. Sizni qaytarib olib boramiz.",
        'ru': "Страница, которую вы ищете, либо перенесена, либо архивирована, либо никогда не существовала. Давайте вернёмся на правильный путь.",
        'en': "The page you're looking for has either been moved, archived, or never existed in the first place. Let's get you back on track.",
    },
    'error_500_headline': {
        'xo': 'Bizning tomonda<br><em style="font-weight: 400;">nimadir uzilibdi.</em>',
        'uz': 'Bizning tomonda<br><em style="font-weight: 400;">nimadir uzilibdi.</em>',
        'ru': 'У нас тут<br><em style="font-weight: 400;">что-то сломалось.</em>',
        'en': 'Something on our<br><em style="font-weight: 400;">end snapped.</em>',
    },
    'error_500_description': {
        'xo': "Ichki xato yuz berdi, sahifa chiqmadi. Jamoaga xabar yetib bordi — bir oz vaqtdan keyin urinib ko'ring yoki bosh sahifaga qayting.",
        'uz': "Ichki xato yuz berdi, sahifa render qilolmadi. Jamoaga xabar yuborildi — bir oz kutib qayta urinib ko'ring yoki bosh sahifaga qayting.",
        'ru': "Произошла внутренняя ошибка, страница не отрендерилась. Команда уже в курсе — попробуйте через минуту или вернитесь на главную.",
        'en': "An internal error occurred and the page couldn't render. The team has been notified — try again in a moment, or head back home.",
    },
    'error_unavailable_headline': {
        'xo': 'Bu bo\'lim<br><em style="font-weight: 400;">vaqtincha o\'chirilgan.</em>',
        'uz': 'Bu bo\'lim<br><em style="font-weight: 400;">vaqtincha o\'chirilgan.</em>',
        'ru': 'Этот раздел<br><em style="font-weight: 400;">временно отключён.</em>',
        'en': 'This section is<br><em style="font-weight: 400;">temporarily offline.</em>',
    },
    'error_unavailable_description': {
        'xo': "Saytning bu qismi vaqtincha o'chirilgan. Tezda qaytadi — bir oz keyin tekshiring.",
        'uz': "Saytning bu qismi vaqtincha o'chirilgan. Tez orada qayta yoqiladi — keyinroq tekshiring.",
        'ru': "Эта часть сайта временно отключена. Скоро вернётся — загляните позже.",
        'en': "This part of the site is temporarily offline. Check back soon — it should be up again shortly.",
    },
    'availability_badge': {
        'xo': "Q2 2026 · qabul qilamiz",
        'uz': "Q2 2026 · qabul qilinmoqda",
        'ru': "Q2 2026 · принимаем",
        'en': "Now booking · Q2 2026",
    },
}


# JSON list/dict fields — handled separately
TICKER = {
    'xo': ["VibeCoder", "AI yordamida dasturlash", "Web ilovalar · Telegram botlar · Full-stack",
           "Toshkent — dunyo bo'yicha remote", "Demolar uchun emas, kattalashish uchun yasalgan"],
    'uz': ["VibeCoder", "AI-yordamchi rivojlanish", "Web ilovalar · Telegram botlar · Full-stack",
           "Toshkent — global remote", "Demo uchun emas, scale uchun yaratilgan"],
    'ru': ["VibeCoder", "AI-augmented разработка", "Веб-приложения · Telegram-боты · Full-stack",
           "Ташкент — удалённо по всему миру", "Создано для масштаба, не для демо"],
    'en': ["VibeCoder", "AI-augmented development", "Web apps · Telegram bots · Full-stack",
           "Tashkent — worldwide remote", "Built for scale, not for demos"],
}

MANIFESTO = {
    'xo': [
        {'n': '01', 'title': "Kod aniq fikrlashning yon natijasi.",
         'description': "Toza kodbaza muammoni aniq tushunishning izi. Spaghetti yozib, uni 'pragmatik' deb atamayman."},
        {'n': '02', 'title': "Production yagona muhim fikr.",
         'description': "Demolar — teatr. Men ishimni App Store sharhlari, crash-free seanslar va mijozlar sanay oladigan daromad bilan o'lchayman."},
        {'n': '03', 'title': "Zerikarli infrastruktura — eng yuqori daraja.",
         'description': "Hech qachon to'xtamaydigan CI. Ma'lumotni yo'qotmaydigan migratsiyalar. Haqiqatda foydalanuvchi observability. Diqqat tortmaydigan qismlar — bu yerda senior muhandis o'z haqini oladi."},
    ],
    'uz': [
        {'n': '01', 'title': "Kod — aniq fikrlashning natijasi.",
         'description': "Toza kodbaza muammoni aniq tushunishning quyqasidir. Men spaghetti yozib, uni 'pragmatik' deb atamayman."},
        {'n': '02', 'title': "Production — yagona muhim fikr.",
         'description': "Demolar teatrdir. O'z ishimni App Store sharhlari, crash-free sessiyalar va mijozlar hisoblay oladigan daromad bilan o'lchayman."},
        {'n': '03', 'title': "Zerikarli infratuzilma — yuksak mahorat.",
         'description': "Hech qachon ishdan chiqmaydigan CI. Ma'lumotni yo'qotmaydigan migratsiyalar. Haqiqatda foydalaniladigan observability. Diqqat tortmaydigan qismlar — senior muhandislarning haqi shu yerda."},
    ],
    'ru': [
        {'n': '01', 'title': "Код — побочный эффект ясного мышления.",
         'description': "Чистый код — это след чёткого понимания задачи. Я не пишу спагетти и не называю это прагматизмом."},
        {'n': '02', 'title': "Production — единственное мнение, которое имеет значение.",
         'description': "Демо — это театр. Я измеряю свою работу отзывами в App Store, crash-free сессиями и реальной выручкой клиента."},
        {'n': '03', 'title': "Скучная инфраструктура — высочайшее мастерство.",
         'description': "CI, который никогда не падает. Миграции, которые не теряют данные. Observability, которую реально используешь. Незрелищные части — там senior получает свою зарплату."},
    ],
    'en': [
        {'n': '01', 'title': "Code is a side effect of thinking clearly.",
         'description': "A clean codebase is the residue of a clear understanding of the problem. I don't ship spaghetti and call it pragmatic."},
        {'n': '02', 'title': "Production is the only opinion that matters.",
         'description': "Demos are theatre. I measure my work by App Store reviews, crash-free sessions, and revenue clients can count."},
        {'n': '03', 'title': "Boring infrastructure is high craft.",
         'description': "CI that never fails. Migrations that never lose data. Observability you actually use. The unglamorous parts are where senior engineers earn their fee."},
    ],
}

PROCESS = {
    'xo': [
        {'n': '01', 'title': "Tashxis", 'description': "60-daqiqalik suhbat. Brif ortidagi haqiqiy muammoni xaritalaymiz — simptomni emas."},
        {'n': '02', 'title': "Loyihalash", 'description': "1-haftalik sprint: data model, state shape, integration surfaces. Hali kod yo'q."},
        {'n': '03', 'title': "Vertikal qatlamlarda yasaymiz", 'description': "Har hafta uchidan-uchiga ishlayotgan funksiyalar. 7-kundan staging deploy, AI bilan tezroq iteratsiya."},
        {'n': '04', 'title': "Qo'rg'on + ishga tushirish", 'description': "Real foydalanuvchilar bilan beta, telemetriya ulanadi, rollback rejasi tayyor. Keyin bir buyruq bilan production deploy."},
        {'n': '05', 'title': "Operatsiya", 'description': "Ixtiyoriy retainer. Inssidentlarga reaksiya, telemetriya tahlili — sahnani ushlab turadigan zerikarli o'rta."},
    ],
    'uz': [
        {'n': '01', 'title': "Diagnostika", 'description': "60-daqiqalik suhbat. Brif ortidagi haqiqiy muammoni aniqlaymiz — simptomni emas."},
        {'n': '02', 'title': "Arxitektura", 'description': "1-haftalik sprint: data model, holat strukturasi, integratsiya yuzalari. Hali kod yo'q."},
        {'n': '03', 'title': "Vertikal slice'larda quramiz", 'description': "Har hafta to'liq ishlovchi funksiyalar. 7-kundan staging deploy, AI bilan tezlashgan iteratsiya."},
        {'n': '04', 'title': "Mustahkamlash + ishga tushirish", 'description': "Real foydalanuvchilar bilan beta, telemetriya ulanadi, rollback rejasi tayyor. Keyin bir buyruqda production deploy."},
        {'n': '05', 'title': "Operatsiya", 'description': "Ixtiyoriy retainer. Insidentlar, telemetriya tahlili — uzoq muddat ishlab turishni ta'minlovchi zerikarli o'rta."},
    ],
    'ru': [
        {'n': '01', 'title': "Диагностика", 'description': "60-минутный звонок. Картируем настоящую проблему за брифом — не симптом."},
        {'n': '02', 'title': "Архитектура", 'description': "1-недельный спринт: модель данных, состояние, интеграционные поверхности. Кода ещё нет."},
        {'n': '03', 'title': "Строим вертикальными срезами", 'description': "Каждую неделю — полнофункциональные фичи end-to-end. С 7-го дня staging-деплой, AI ускоряет итерацию."},
        {'n': '04', 'title': "Закаляем + запускаем", 'description': "Бета с реальными пользователями, телеметрия, план отката готов. Потом production-деплой одной командой."},
        {'n': '05', 'title': "Эксплуатация", 'description': "Опциональный retainer. Реакция на инциденты, разбор телеметрии — скучная середина, которая держит проект на плаву."},
    ],
    'en': [
        {'n': '01', 'title': "Diagnose", 'description': "A 60-minute call. We map the actual problem behind the brief — not the symptom."},
        {'n': '02', 'title': "Architect", 'description': "A 1-week sprint to lay out the data model, state shape, integration surfaces. No code yet."},
        {'n': '03', 'title': "Build in slices", 'description': "End-to-end working features each week. Staging deploy from day 7, AI-augmented iteration."},
        {'n': '04', 'title': "Harden + ship", 'description': "Beta with real users, telemetry wired, rollback plan agreed. Then production deploy with one command."},
        {'n': '05', 'title': "Operate", 'description': "Optional retainer. Incident triage, telemetry reviews — the boring middle that keeps things alive."},
    ],
}

TEAM_VALUES = {
    'xo': [
        {'title': "Toza kod", 'description': "Keyingi muhandis uchrashuvsiz o'qiy oladigan kod."},
        {'title': "Kattalashadigan arxitektura", 'description': "v1 emas — v3 uchun yasalgan."},
        {'title': "Mahsulot fikri", 'description': "'Qanday'dan oldin 'nima uchun'ni so'raymiz."},
        {'title': "Tez yetkazib berish", 'description': "Ikki haftalik sprint, juma kuni demo, syurprizsiz."},
        {'title': "Uzoq muddatli qo'llab-quvvatlash", 'description': "Topshirib, ko'zdan g'oyib bo'lmaymiz."},
        {'title': "Production-birinchi", 'description': "Real foydalanuvchilar, real sharhlar, real daromad."},
    ],
    'uz': [
        {'title': "Toza kod", 'description': "Keyingi muhandis uchrashuvsiz o'qiy oladigan kod."},
        {'title': "Scalable arxitektura", 'description': "v1 emas — v3 uchun qurilgan."},
        {'title': "Mahsulot fikri", 'description': "'Qanday'dan oldin 'nima uchun'ni so'raymiz."},
        {'title': "Tezkor yetkazib berish", 'description': "Ikki haftalik sprint, juma kuni demo, kutilmagansiz."},
        {'title': "Uzoq muddatli qo'llab-quvvatlash", 'description': "Topshirib, ko'rinmay qolmaymiz."},
        {'title': "Production-birinchi", 'description': "Real foydalanuvchilar, real sharhlar, real daromad."},
    ],
    'ru': [
        {'title': "Чистый код", 'description': "Код, который следующий инженер прочтёт без созвона."},
        {'title': "Масштабируемая архитектура", 'description': "Сделано для v3 — не только v1."},
        {'title': "Продуктовое мышление", 'description': "Спрашиваем 'почему' перед 'как'."},
        {'title': "Быстрая доставка", 'description': "Двухнедельные спринты, демо в пятницу, без сюрпризов."},
        {'title': "Долгая поддержка", 'description': "Не передаём проект и не исчезаем."},
        {'title': "Production-first", 'description': "Реальные пользователи, реальные отзывы, реальная выручка."},
    ],
    'en': [
        {'title': "Clean code", 'description': "Code that the next engineer can read without a meeting."},
        {'title': "Scalable architecture", 'description': "Built for v3 — not just v1."},
        {'title': "Product thinking", 'description': "We ask 'why' before 'how'."},
        {'title': "Fast delivery", 'description': "Two-week sprints, Friday demos, no surprises."},
        {'title': "Long-term support", 'description': "We don't hand off and disappear."},
        {'title': "Production-first", 'description': "Real users, real reviews, real revenue."},
    ],
}

PRACTICE = {
    'xo': ["Web ilovalar · Django", "Telegram botlar · Aiogram", "AI-yordamlashgan tizimlar", "Dizayn tizimlari"],
    'uz': ["Web ilovalar · Django", "Telegram botlar · Aiogram", "AI-yordamchi tizimlar", "Dizayn tizimlari"],
    'ru': ["Веб-приложения · Django", "Telegram-боты · Aiogram", "AI-augmented системы", "Дизайн-системы"],
    'en': ["Web apps · Django", "Telegram bots · Aiogram", "AI-augmented systems", "Design systems"],
}


def translate(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for row in SiteSettings.objects.all():
        for field, by_lang in T.items():
            for lang, value in by_lang.items():
                attr = f"{field}_{lang}"
                if hasattr(row, attr):
                    setattr(row, attr, value)
        # JSON list fields
        for lang, items in TICKER.items():
            attr = f"ticker_items_{lang}"
            if hasattr(row, attr):
                setattr(row, attr, items)
        for lang, items in MANIFESTO.items():
            attr = f"manifesto_principles_{lang}"
            if hasattr(row, attr):
                setattr(row, attr, items)
        for lang, items in PROCESS.items():
            attr = f"process_steps_{lang}"
            if hasattr(row, attr):
                setattr(row, attr, items)
        for lang, items in TEAM_VALUES.items():
            attr = f"team_values_{lang}"
            if hasattr(row, attr):
                setattr(row, attr, items)
        for lang, items in PRACTICE.items():
            attr = f"footer_practice_items_{lang}"
            if hasattr(row, attr):
                setattr(row, attr, items)
        row.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0035_asset_alt_text_en_asset_alt_text_ru_and_more'),
    ]
    operations = [
        migrations.RunPython(translate, noop),
    ]
