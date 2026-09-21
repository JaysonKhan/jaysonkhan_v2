"""Create/update key EdTech projects for jaysonkhan.com.

Idempotent; deploy.sh runs it on every deploy — these Project rows are
code-owned. Facts checked 2026-09-21 through read-only production counts and current
JaysonServer repositories; definitions and exact counts: docs/project-facts-2026-09.md. The legacy standalone `talabaovozi` card is
hidden here: TalabaOvozi was rebranded into EduStats (web + @TalabaOvvoziBot),
so one card tells that story.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

LANGS = ("xo", "uz", "ru", "en")

PROJECTS = [{'slug': 'uzexam',
  'web_page_url': 'https://uzexam.uz/',
  'order': -100,
  'stats': [{'v': '85k+', 'l': 'Published questions', 'as_of': '2026-09-21'},
            {'v': '21k+', 'l': 'Registered users', 'as_of': '2026-09-21'},
            {'v': '7', 'l': 'Mobile apps', 'as_of': '2026-09-21'}],
  'title': {'xo': 'UzExam — AI bilan kuchaytirilgan imtihon platformasi',
            'uz': 'UzExam — AI bilan kuchaytirilgan imtihon platformasi',
            'ru': 'UzExam — AI-усиленная экзаменационная платформа',
            'en': 'UzExam — AI-powered exam platform'},
  'short_description': {'xo': "85k+ ochiq savol, imtihon yo‘nalishla (DTM, IELTS, SAT, Avtotest...), "
                              "takrorlanmas savolla, SM-2 va antifraud reyting — hammasi Telegram bilan "
                              "chambarchas.",
                        'uz': "85k+ ochiq savol, 21k+ ro'yxatdan o'tgan foydalanuvchi va 7 mobil ilova. "
                              'IELTS, Multilevel, SAT, DTM, Milliy sertifikat, Avtotest va Intervyu — web, '
                              "Telegram va Flutter'da.",
                        'ru': '85k+ опубликованных вопросов, 21k+ зарегистрированных пользователей и 7 '
                              'мобильных приложений: IELTS, Multilevel, SAT, DTM, национальный сертификат, '
                              'автотест и интервью.',
                        'en': '85k+ published questions, 21k+ registered users and 7 mobile apps: IELTS, '
                              'Multilevel, SAT, DTM, national certification, driving tests and interviews.'},
  'description_rich': {'xo': "<p><strong>UzExam</strong> (uzexam.uz) — O'zbekiston uchun universal, "
                             "adaptiv imtihon platformasi: 85k+ ochiq savol, imtihon yo‘nalishla — "
                             "Abituriyent (DTM), IELTS, SAT, Avtotest, maktab va universitet "
                             "imtihonla.</p><p>Farqi dvigatelda: <strong>Uniqueness Engine</strong> "
                             "savollarni har foydalanuvchi uchun 90 kun takrorlatmaydi, "
                             "<strong>SM-2</strong> xatolaringni o'z vaqtida qaytarib turadi, antifraud "
                             "reyting esa jadvalni halol saqlaydi. B2B tenant tizimi, Click/Telegram "
                             "Stars to'lovla va AI mentor qatlami (Claude esse baholash bilan) ekotizimni"
                             " to'ldiradi.</p><p>3 oyda yolg'iz, 24/7 AI-agentla bilan qurilgan — 7 mobil"
                             " ilova, 21k+ ro'yxatdan o'tgan foydalanuvchi. President Tech Award 2026 "
                             "ishtirokchisi.</p>",
                       'uz': "<p><strong>UzExam</strong> — 85k+ ochiq savol, 21k+ ro'yxatdan o'tgan "
                             'foydalanuvchi va 7 mobil ilova. IELTS, Multilevel, SAT, DTM, Milliy '
                             "sertifikat, Avtotest va Intervyu — web, Telegram va Flutter'da.</p><p>IELTS va "
                             'Multilevel mashqlari, SAT modullari, savol banki va AI yozma ish tekshiruvi. '
                             'Yetti mobil ilova yagona backend, hisob va qurilma sessiyalari orqali '
                             'ishlaydi.</p>',
                       'ru': '<p><strong>UzExam</strong> — 85k+ опубликованных вопросов, 21k+ '
                             'зарегистрированных пользователей и 7 мобильных приложений: IELTS, Multilevel, '
                             'SAT, DTM, национальный сертификат, автотест и интервью.</p><p>Практика IELTS и '
                             'Multilevel, модули SAT, банк вопросов и AI-проверка письменных работ. Веб, '
                             'Telegram и семь Flutter-приложений используют единый backend, аккаунт и '
                             'управление сессиями устройств.</p>',
                       'en': '<p><strong>UzExam</strong> — 85k+ published questions, 21k+ registered users '
                             'and 7 mobile apps: IELTS, Multilevel, SAT, DTM, national certification, '
                             'driving tests and interviews.</p><p>IELTS and Multilevel practice, SAT '
                             'modules, a question bank and AI writing assessment. Web, Telegram and seven '
                             'Flutter apps share one backend, account and device-session management.</p>'},
  'skills': ['Flutter', 'Django', 'PostgreSQL', 'AI Mentors']},
 {'slug': 'edustats',
  'web_page_url': 'https://edustats.uz/',
  'order': -90,
  'stats': [{'v': '53k+', 'l': 'Telegram users', 'as_of': '2026-09-21'},
            {'v': '193', 'l': 'University listings', 'as_of': '2026-09-21'},
            {'v': '121', 'l': 'Universities with scores', 'as_of': '2026-09-21'}],
  'title': {'xo': "EduStats — talabalar fikri va ta'lim analitikasi",
            'uz': "EduStats — talabalar fikri va ta'lim analitikasi",
            'ru': 'EduStats — голос студентов и образовательная аналитика',
            'en': 'EduStats — student voice & education analytics'},
  'short_description': {'xo': "O'zbekiston talabalar fikri platformasi: universitetla haqida tasdiqlangan"
                              " fikrla va reytingla, 53k+ Telegram auditoriya, 121 OTM "
                              "o'tish ballari (2020–2025).",
                        'uz': "53k+ Telegram foydalanuvchi, katalogda 193 faol OTM va 121 OTM bo'yicha "
                              "o'tish ballari. Talabalar fikri, reytinglar va manbali ta'lim statistikasi "
                              'bir joyda.',
                        'ru': '53k+ пользователей Telegram, 193 активных вуза в каталоге и проходные баллы '
                              'для 121 вуза. Отзывы студентов, рейтинги и статистика образования с указанием '
                              'источников.',
                        'en': '53k+ Telegram users, 193 active university listings and admission scores for '
                              '121 universities. Student reviews, rankings and source-backed education '
                              'statistics.'},
  'description_rich': {'xo': "<p><strong>EduStats</strong> (edustats.uz) — O'zbekiston talabalar fikri va"
                             " ta'lim analitikasi platformasi: talabala universitet va o'qituvchilarni "
                             "ochiq baholaydi, reyting halol qoladi — pul ko'rinishni sotib olishi "
                             "mumkin, ballni hech qachon.</p><p>Ekotizim web platforma + "
                             "<strong>@TalabaOvvoziBot</strong>'dan iborat — 53k+ Telegram "
                             "foydalanuvchili auditoriya. Haftalik TOP fikrla kanalga avtomatik chiqadi, "
                             "AI sentiment tahlili fikrlarni signalga aylantiradi, 121 OTM o'tish ballari"
                             " (2020–2025) esa qabul mavsumida trafik magniti.</p>",
                       'uz': '<p><strong>EduStats</strong> — 53k+ Telegram foydalanuvchi, katalogda 193 faol '
                             "OTM va 121 OTM bo'yicha o'tish ballari. Talabalar fikri, reytinglar va manbali "
                             "ta'lim statistikasi bir joyda.</p><p>Web va @TalabaOvvoziBot: universitetlar "
                             "va o'qituvchilar haqidagi fikrlar, qabul analitikasi, 2020–2025 o'tish ballari "
                             'va ulashiladigan statistika sahifalari. Auditoriya soni jami bot '
                             'foydalanuvchilarini bildiradi, telefon orqali tasdiqlanganlarni emas.</p>',
                       'ru': '<p><strong>EduStats</strong> — 53k+ пользователей Telegram, 193 активных вуза '
                             'в каталоге и проходные баллы для 121 вуза. Отзывы студентов, рейтинги и '
                             'статистика образования с указанием источников.</p><p>Веб и @TalabaOvvoziBot: '
                             'отзывы о вузах и преподавателях, аналитика поступления, проходные баллы за '
                             '2020–2025 годы и страницы статистики для обмена. Аудитория — все пользователи '
                             'бота, а не число подтверждённых телефонов.</p>',
                       'en': '<p><strong>EduStats</strong> — 53k+ Telegram users, 193 active university '
                             'listings and admission scores for 121 universities. Student reviews, rankings '
                             'and source-backed education statistics.</p><p>Web and @TalabaOvvoziBot combine '
                             'university and faculty reviews, admissions analytics, 2020–2025 cut-off scores '
                             'and shareable statistics pages. Audience means registered bot users, not '
                             'phone-verified accounts.</p>'},
  'skills': ['Django', 'aiogram', 'Education Analytics', 'AI Sentiment']},
 {'slug': 'vaygo',
  'web_page_url': 'https://vaygo.uz/',
  'order': -80,
  'title': {'xo': 'Vaygo — video savdo va AI sotuvchi',
            'uz': 'Vaygo — video savdo va AI sotuvchi',
            'ru': 'Vaygo — видеоторговля и AI-продавец',
            'en': 'Vaygo — video commerce & AI sales'},
  'stats': [],
  'skills': ['Django', 'aiogram', 'PostgreSQL', 'AI Sales'],
  'short_description': {'xo': "Video orqali mahsulot kashf qilish, istaklar ro'yxati va Telegram'dagi AI "
                              "sotuvchi. Xaridor signallari qaysi mahsulotga talab borligini ko'rsatadi.",
                        'uz': "Video orqali mahsulot kashf qilish, istaklar ro'yxati va Telegram'dagi AI "
                              "sotuvchi. Xaridor signallari qaysi mahsulotga talab borligini ko'rsatadi.",
                        'ru': 'Видеокаталог, список желаний и AI-продавец в Telegram. Сигналы интереса '
                              'покупателей помогают понять спрос на товары.',
                        'en': 'Video-led product discovery, wishlists and a Telegram AI sales assistant. '
                              'Customer interest signals help identify demand.'},
  'description_rich': {'xo': '<p><strong>Vaygo</strong> — Video orqali mahsulot kashf qilish, istaklar '
                             "ro'yxati va Telegram'dagi AI sotuvchi. Xaridor signallari qaysi mahsulotga "
                             "talab borligini ko'rsatadi.</p><p>Vaygo web-do'kon va Telegram botni "
                             'birlashtiradi: video katalog, wishlist, mahsulotga qiziqish signallari va AI '
                             "sotuvchi bilan suhbat. Mahsulotla va buyurtmala yagona backend'da "
                             'yuritiladi.</p>',
                       'uz': '<p><strong>Vaygo</strong> — Video orqali mahsulot kashf qilish, istaklar '
                             "ro'yxati va Telegram'dagi AI sotuvchi. Xaridor signallari qaysi mahsulotga "
                             "talab borligini ko'rsatadi.</p><p>Vaygo web-do'kon va Telegram botni "
                             'birlashtiradi: video katalog, wishlist, mahsulotga qiziqish signallari va AI '
                             "sotuvchi bilan suhbat. Mahsulotlar va buyurtmalar yagona backend'da "
                             'yuritiladi.</p>',
                       'ru': '<p><strong>Vaygo</strong> — Видеокаталог, список желаний и AI-продавец в '
                             'Telegram. Сигналы интереса покупателей помогают понять спрос на '
                             'товары.</p><p>Vaygo объединяет веб-магазин и Telegram-бот: видео, список '
                             'желаний, сигналы интереса и диалог с AI-продавцом. Товары и заказы хранятся в '
                             'едином backend.</p>',
                       'en': '<p><strong>Vaygo</strong> — Video-led product discovery, wishlists and a '
                             'Telegram AI sales assistant. Customer interest signals help identify '
                             'demand.</p><p>Vaygo connects a web storefront and Telegram bot through a video '
                             'catalog, wishlists, interest signals and an AI sales assistant. Products and '
                             'orders share one backend.</p>'}}]

# TalabaOvozi was rebranded into EduStats (web + @TalabaOvvoziBot are one
# product) — hide the legacy standalone card instead of showing a duplicate.
HIDE_SLUGS = ("talabaovozi",)


def set_translated(obj, field, values):
    for lang in LANGS:
        attr = f"{field}_{lang}"
        if hasattr(obj, attr):
            setattr(obj, attr, values[lang])
        elif lang == "xo" and hasattr(obj, field):
            setattr(obj, field, values[lang])


class Command(BaseCommand):
    help = "Refresh verified UzExam, EduStats and Vaygo project facts."

    @transaction.atomic
    def handle(self, *args, **options):
        from portfolio.models import Project, Skill

        for data in PROJECTS:
            project, _ = Project.objects.get_or_create(slug=data["slug"], defaults={"title": data["title"]["xo"]})
            for field in ("title", "short_description", "description_rich"):
                set_translated(project, field, data[field])
            project.web_page_url = data["web_page_url"]
            project.stats = data["stats"]
            project.order = data["order"]
            project.is_featured = True
            project.is_visible = True
            project.is_bot = False
            project.save()
            skills = [Skill.objects.get_or_create(name=name, defaults={"category": "architecture"})[0]
                      for name in data["skills"]]
            project.technologies.set(skills)
            self.stdout.write(self.style.SUCCESS(f"Updated project: {project.slug}"))

        hidden = Project.objects.filter(slug__in=HIDE_SLUGS, is_visible=True).update(
            is_visible=False, is_featured=False
        )
        if hidden:
            self.stdout.write(self.style.SUCCESS(
                f"Hidden {hidden} legacy project card(s): {', '.join(HIDE_SLUGS)} (folded into EduStats)."
            ))
