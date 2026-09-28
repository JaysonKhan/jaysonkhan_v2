"""Career dates confirmed by the owner on 2026-09-28; copy comes from the resumes."""
from django.db import migrations
from django.db.models import Q

ROWS = [{'match': 'Consort',
  'start_date': '2026-06-01',
  'end_date': None,
  'defaults': {'company': 'Consort Group LLC',
               'position': 'Mobile Developer',
               'description': 'Growz va Bizon ilovalari ustida ishlayman. Hozir ikkala mobil '
                              'mahsulotga AI integratsiya qilish va xarita funksiyalarini ishlab '
                              'chiqish bilan shug‘ullanaman.',
               'location': 'Tashkent, Uzbekistan',
               'company_xo': 'Consort Group LLC',
               'position_xo': 'Mobile Developer',
               'description_xo': 'Growz va Bizon ilovalari ustida ishlayman. Hozir ikkala mobil '
                                 'mahsulotga AI integratsiya qilish va xarita funksiyalarini '
                                 'ishlab chiqish bilan shug‘ullanaman.',
               'company_uz': 'Consort Group LLC',
               'position_uz': 'Mobile Developer',
               'description_uz': 'Growz va Bizon ilovalari ustida ishlayman. Hozir ikkala mobil '
                                 'mahsulotga AI integratsiya qilish va xarita funksiyalarini '
                                 'ishlab chiqish bilan shug‘ullanaman.',
               'company_ru': 'Consort Group LLC',
               'position_ru': 'Mobile Developer',
               'description_ru': 'Работаю над приложениями Growz и Bizon. Сейчас занимаюсь '
                                 'интеграцией AI в оба мобильных продукта и разработкой функций '
                                 'карты.',
               'company_en': 'Consort Group LLC',
               'position_en': 'Mobile Developer',
               'description_en': 'Develop Flutter features for Growz and Bizon. Current work '
                                 'focuses on integrating AI into both mobile products and building '
                                 'and improving map features.'}},
 {'match': 'UzExam',
  'start_date': '2026-04-01',
  'end_date': None,
  'defaults': {'company': 'UzExam.uz',
               'position': 'Founder & AI EdTech Specialist',
               'description': "85k+ ochiq savol, 21k+ ro'yxatdan o'tgan foydalanuvchi va 7 mobil "
                              'ilova. IELTS, Multilevel, SAT, DTM, Milliy sertifikat, Avtotest va '
                              "Intervyu — web, Telegram va Flutter'da.",
               'location': 'Tashkent, Uzbekistan',
               'company_xo': 'UzExam.uz',
               'position_xo': 'Founder & AI EdTech Specialist',
               'description_xo': "85k+ ochiq savol, 21k+ ro'yxatdan o'tgan foydalanuvchi va 7 "
                                 'mobil ilova. IELTS, Multilevel, SAT, DTM, Milliy sertifikat, '
                                 "Avtotest va Intervyu — web, Telegram va Flutter'da.",
               'company_uz': 'UzExam.uz',
               'position_uz': 'Asoschi va Mobile / Full-Stack Developer',
               'description_uz': 'UzExam asoschisi sifatida IELTS, Multilevel, SAT, DTM, Milliy '
                                 'sertifikat, Avtotest va Intervyu uchun yettita Flutter ilovasini '
                                 'ishlab chiqaman. Umumiy mobil arxitektura, autentifikatsiya, '
                                 'mashqlar, obuna va Django backendini yuritaman. EduStats ta’lim '
                                 'platformasini ham yaratganman.',
               'company_ru': 'UzExam.uz',
               'position_ru': 'Основатель и Mobile / Full-Stack Developer',
               'description_ru': 'Основал UzExam и разрабатываю семь Flutter-приложений: IELTS, '
                                 'Multilevel, SAT, DTM, Milliy sertifikat, Avtotest и Intervyu. '
                                 'Поддерживаю общую мобильную архитектуру, авторизацию, '
                                 'тренировочные задания, подписки и Django-бэкенд. Также создал '
                                 'образовательную платформу EduStats.',
               'company_en': 'UzExam.uz',
               'position_en': 'Founder & Mobile / Full-Stack Developer',
               'description_en': 'Founded UzExam and develop seven Flutter apps: IELTS, '
                                 'Multilevel, SAT, DTM, Milliy sertifikat, Avtotest and Intervyu. '
                                 'Maintain shared mobile architecture, authentication, practice '
                                 'flows, subscriptions and the Django backend. Also created the '
                                 'EduStats education platform.'}},
 {'match': 'Soliq',
  'start_date': '2026-01-01',
  'end_date': '2026-04-30',
  'defaults': {'company': 'Soliq servis AJ',
               'position': 'Software Engineer — Flutter / Fintech',
               'description': "TaxPay fintech to'lov ilovasini noldan qurdim: Flutter + Clean "
                              'Architecture, karta ulash, OTP, tranzaksiyala va PCI talablariga '
                              'mos REST integratsiyala. Ilova production-ready darajaga '
                              'yetkazildi.',
               'location': 'Tashkent, Uzbekistan',
               'company_xo': 'Soliq servis AJ',
               'position_xo': 'Software Engineer — Flutter / Fintech',
               'description_xo': "TaxPay fintech to'lov ilovasini noldan qurdim: Flutter + Clean "
                                 'Architecture, karta ulash, OTP, tranzaksiyala va PCI talablariga '
                                 'mos REST integratsiyala. Ilova production-ready darajaga '
                                 'yetkazildi.',
               'company_uz': 'Soliq servis AJ',
               'position_uz': 'Flutter Developer · TaxPay',
               'description_uz': 'TaxPay to‘lov ilovasini Flutter, Clean Architecture va BLoC '
                                 'asosida qurdim. Karta ulash, OTP, to‘lovlar va tranzaksiyalar '
                                 'tarixini ishlab chiqdim. Ilova ishga tushirishga tayyor holatga '
                                 'yetkazildi, ammo bo‘lim yopilgach ommaga chiqarilmadi.',
               'company_ru': 'Soliq servis AJ',
               'position_ru': 'Flutter Developer · TaxPay',
               'description_ru': 'Разработал TaxPay на Flutter с Clean Architecture и BLoC: '
                                 'привязка карт, OTP, платежи и история транзакций. Приложение '
                                 'было готово к запуску, но после закрытия отдела не вышло в '
                                 'публичный доступ.',
               'company_en': 'Soliq servis AJ',
               'position_en': 'Flutter Developer · TaxPay',
               'description_en': 'Built TaxPay with Flutter, Clean Architecture and BLoC: card '
                                 'binding, OTP verification, payments and transaction history. '
                                 'Delivered the app to a production-ready stage; it was not '
                                 'publicly released after the department closed.'}},
 {'match': 'AIBA',
  'start_date': '2025-08-01',
  'end_date': '2025-11-30',
  'defaults': {'company': 'AI Business Assistant (AIBA)',
               'position': 'Mobile Team Lead — AI Business Assistant',
               'description': 'AIBA loyihasida mobil jamoaga yetakchilik qildim: AI vositala, '
                              'generativ servisla va aqlli assistent funksiyalarini mobil '
                              "ilovalarga qo'shdik; code review va mentorlik manda edi.",
               'location': 'Tashkent, Uzbekistan',
               'company_xo': 'AI Business Assistant (AIBA)',
               'position_xo': 'Mobile Team Lead — AI Business Assistant',
               'description_xo': 'AIBA loyihasida mobil jamoaga yetakchilik qildim: AI vositala, '
                                 'generativ servisla va aqlli assistent funksiyalarini mobil '
                                 "ilovalarga qo'shdik; code review va mentorlik manda edi.",
               'company_uz': 'AI Business Assistant (AIBA)',
               'position_uz': 'Mobile Team Lead · AI Business Assistant',
               'description_uz': 'AI assistent funksiyalari, autentifikatsiya, '
                                 'push-bildirishnomalar, SQLite orqali oflayn saqlash va ko‘p '
                                 'tilli interfeys ustida ishladim. Mobil jamoa vazifalarini '
                                 'muvofiqlashtirdim, kodni ko‘rib chiqish va dasturchilarga yordam '
                                 'berishda qatnashdim.',
               'company_ru': 'AI Business Assistant (AIBA)',
               'position_ru': 'Mobile Team Lead · AI Business Assistant',
               'description_ru': 'Работал над функциями AI-ассистента, авторизацией, '
                                 'push-уведомлениями, офлайн-хранилищем SQLite и многоязычным '
                                 'интерфейсом. Координировал задачи мобильной команды, участвовал '
                                 'в ревью кода и помогал разработчикам.',
               'company_en': 'AI Business Assistant (AIBA)',
               'position_en': 'Mobile Team Lead · AI Business Assistant',
               'description_en': 'Worked on AI assistant features, authentication, push '
                                 'notifications, SQLite offline storage and multilingual '
                                 'interfaces. Coordinated mobile tasks, reviewed code and '
                                 'supported other developers.'}},
 {'match': 'UIC',
  'start_date': '2023-09-01',
  'end_date': '2025-12-31',
  'defaults': {'company': 'UIC Group',
               'position': 'Flutter Mobile Engineer',
               'description': '20+ korporativ mobil ilova qurdim (Flutter, Clean Architecture, '
                              'BLoC): yuklanishni ~40% tezlashtirdim, 15+ REST API, audio/video '
                              "streaming, to'lov tizimla va murakkab animatsiyala. CI/CD yo'lga "
                              "qo'yishda qatnashdim.",
               'location': 'Tashkent, Uzbekistan',
               'company_xo': 'UIC Group',
               'position_xo': 'Flutter Mobile Engineer',
               'description_xo': '20+ korporativ mobil ilova qurdim (Flutter, Clean Architecture, '
                                 'BLoC): yuklanishni ~40% tezlashtirdim, 15+ REST API, audio/video '
                                 "streaming, to'lov tizimla va murakkab animatsiyala. CI/CD yo'lga "
                                 "qo'yishda qatnashdim.",
               'company_uz': 'UIC Group',
               'position_uz': 'Flutter Developer',
               'description_uz': 'Android va iOS uchun korporativ Flutter ilovalarini ishlab '
                                 'chiqdim. REST API, mahalliy saqlash, media, to‘lov interfeyslari '
                                 'va ko‘p tilli UI bilan ishladim. Keshlash va refaktoring orqali '
                                 'ilovalarni yaxshiladim; code review, CI/CD va reliz tayyorlashda '
                                 'qatnashdim.',
               'company_ru': 'UIC Group',
               'position_ru': 'Flutter Developer',
               'description_ru': 'Разрабатывал корпоративные Flutter-приложения для Android и iOS. '
                                 'Работал с REST API, локальным хранением, медиа, платёжными '
                                 'интерфейсами и локализацией. Улучшал приложения через '
                                 'кеширование и рефакторинг; участвовал в ревью кода, CI/CD и '
                                 'подготовке релизов.',
               'company_en': 'UIC Group',
               'position_en': 'Flutter Developer',
               'description_en': 'Developed corporate Flutter applications for Android and iOS. '
                                 'Implemented REST integrations, local storage, media playback, '
                                 'payment interfaces and multilingual UI. Improved responsiveness '
                                 'through caching and refactoring; contributed to code reviews, '
                                 'CI/CD and release preparation.'}}]


def refresh_career(apps, schema_editor):
    Experience = apps.get_model("portfolio", "Experience")
    manager = Experience.objects.using(schema_editor.connection.alias)
    for row in ROWS:
        matches = Q(company__icontains=row["match"])
        for lang in ("xo", "uz", "ru", "en"):
            matches |= Q(**{f"company_{lang}__icontains": row["match"]})
        existing = manager.filter(matches)
        dates = {"start_date": row["start_date"], "end_date": row["end_date"],
                 "is_current": row["end_date"] is None}
        if existing.exists():
            existing.update(**dates)
        else:
            manager.create(**row["defaults"], **dates)


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0022_teammember_photo_real")]
    operations = [migrations.RunPython(refresh_career, migrations.RunPython.noop)]
