"""Create/update key EdTech projects for jaysonkhan.com.

Idempotent; deploy.sh runs it on every deploy — these Project rows are
code-owned. Facts source (2026-07): UzExam PTA-2026 docs (60k+ questions,
5.2k users, 9 tracks, 54 modules) and the EduStats rate card (52k+ verified
Telegram users, 75 universities). The legacy standalone `talabaovozi` card is
hidden here: TalabaOvozi was rebranded into EduStats (web + @TalabaOvvoziBot),
so one card tells that story.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

LANGS = ("xo", "uz", "ru", "en")

PROJECTS = [
    {
        "slug": "uzexam",
        "web_page_url": "https://uzexam.uz/",
        "order": -100,
        "stats": [
            {"v": "60k+", "l": "questions"},
            {"v": "5k+", "l": "users"},
            {"v": "9", "l": "exam tracks"},
        ],
        "title": {
            "xo": "UzExam — AI bilan kuchaytirilgan imtihon platformasi",
            "uz": "UzExam — AI bilan kuchaytirilgan imtihon platformasi",
            "ru": "UzExam — AI-усиленная экзаменационная платформа",
            "en": "UzExam — AI-powered exam platform",
        },
        "short_description": {
            "xo": "60k+ savol, 9 imtihon treki (DTM, IELTS, SAT, Avtotest...), takrorlanmas savolla, SM-2 va antifraud reyting — hammasi Telegram bilan chambarchas.",
            "uz": "60k+ savol, 9 imtihon yo'nalishi (DTM, IELTS, SAT, Avtotest...), takrorlanmas savollar, SM-2 va antifraud reyting — Telegram bilan chuqur integratsiya.",
            "ru": "60k+ вопросов, 9 экзаменационных треков (DTM, IELTS, SAT, автотест...), неповторяющиеся вопросы, SM-2 и антифрод-рейтинг — глубокая интеграция с Telegram.",
            "en": "60k+ questions, 9 exam tracks (DTM, IELTS, SAT, driving tests...), non-repeating questions, SM-2 and an anti-fraud rating — deeply integrated with Telegram.",
        },
        "description_rich": {
            "xo": (
                "<p><strong>UzExam</strong> (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi: "
                "60k+ savol, 9 trek — Abituriyent (DTM), IELTS, SAT, Avtotest, maktab va universitet imtihonla.</p>"
                "<p>Farqi dvigatelda: <strong>Uniqueness Engine</strong> savollarni har foydalanuvchi uchun 90 kun "
                "takrorlatmaydi, <strong>SM-2</strong> xatolaringni o'z vaqtida qaytarib turadi, antifraud reyting "
                "esa jadvalni halol saqlaydi. B2B tenant tizimi, Click/Telegram Stars to'lovla va AI mentor qatlami "
                "(Claude esse baholash bilan) ekotizimni to'ldiradi.</p>"
                "<p>3 oyda yolg'iz, 24/7 AI-agentla bilan qurilgan — 54 modul, 100k+ satr kod. "
                "President Tech Award 2026 ishtirokchisi.</p>"
            ),
            "uz": (
                "<p><strong>UzExam</strong> (uzexam.uz) — O'zbekiston uchun universal, adaptiv imtihon platformasi: "
                "60k+ savol, 9 yo'nalish — Abituriyent (DTM), IELTS, SAT, Avtotest, maktab va universitet imtihonlari.</p>"
                "<p>Farqi dvigatelda: <strong>Uniqueness Engine</strong> savollarni har foydalanuvchi uchun 90 kun "
                "takrorlatmaydi, <strong>SM-2</strong> xatolaringizni o'z vaqtida qaytarib turadi, antifraud reyting "
                "esa jadvalni halol saqlaydi. B2B tenant tizimi, Click/Telegram Stars to'lovlar va AI mentor qatlami "
                "(Claude esse baholash bilan) ekotizimni to'ldiradi.</p>"
                "<p>3 oyda yolg'iz, 24/7 AI-agentlar bilan qurilgan — 54 modul, 100k+ satr kod. "
                "President Tech Award 2026 ishtirokchisi.</p>"
            ),
            "ru": (
                "<p><strong>UzExam</strong> (uzexam.uz) — универсальная адаптивная экзаменационная платформа для "
                "Узбекистана: 60k+ вопросов, 9 треков — поступление (DTM), IELTS, SAT, автотест, школьные и "
                "университетские экзамены.</p>"
                "<p>Отличие — в движке: <strong>Uniqueness Engine</strong> не повторяет вопросы 90 дней для каждого "
                "пользователя, <strong>SM-2</strong> возвращает ваши ошибки в нужный момент, антифрод-рейтинг держит "
                "таблицу лидеров честной. B2B-tenant система, платежи Click/Telegram Stars и слой AI-ментора "
                "(включая проверку эссе Claude) завершают экосистему.</p>"
                "<p>Построена в одиночку за 3 месяца с AI-агентами 24/7 — 54 модуля, 100k+ строк кода. "
                "Участник President Tech Award 2026.</p>"
            ),
            "en": (
                "<p><strong>UzExam</strong> (uzexam.uz) is a universal, adaptive exam platform for Uzbekistan: "
                "60k+ questions across 9 tracks — university admissions (DTM), IELTS, SAT, driving tests, school "
                "and university exams.</p>"
                "<p>The engine is the differentiator: the <strong>Uniqueness Engine</strong> keeps questions from "
                "repeating for 90 days per user, <strong>SM-2</strong> spaced repetition brings your mistakes back "
                "at the right moment, and an anti-fraud rating keeps the leaderboard honest. B2B tenants, "
                "Click/Telegram Stars payments and an AI mentor layer (incl. Claude-graded essays) complete the "
                "ecosystem.</p>"
                "<p>Built solo in 3 months with a 24/7 AI-agent workforce — 54 modules, 100k+ lines of code. "
                "President Tech Award 2026 participant.</p>"
            ),
        },
    },
    {
        "slug": "edustats",
        "web_page_url": "https://edustats.uz/",
        "order": -90,
        "stats": [
            {"v": "52k+", "l": "verified users"},
            {"v": "75", "l": "universities"},
            {"v": "AI", "l": "sentiment"},
        ],
        "title": {
            "xo": "EduStats — talabalar fikri va ta'lim analitikasi",
            "uz": "EduStats — talabalar fikri va ta'lim analitikasi",
            "ru": "EduStats — голос студентов и образовательная аналитика",
            "en": "EduStats — student voice & education analytics",
        },
        "short_description": {
            "xo": "O'zbekiston talabalar fikri platformasi: universitetla haqida tasdiqlangan fikrla va reytingla, 52k+ telefon-tasdiqlangan Telegram auditoriya, 75 OTM o'tish ballari (2020–2025).",
            "uz": "O'zbekiston talabalar fikri platformasi: universitetlar haqida tasdiqlangan fikrlar va reytinglar, 52k+ telefon-tasdiqlangan Telegram auditoriya, 75 OTM o'tish ballari (2020–2025).",
            "ru": "Платформа студенческого мнения Узбекистана: верифицированные отзывы и рейтинги университетов, 52k+ телефон-верифицированная Telegram-аудитория, проходные баллы 75 вузов (2020–2025).",
            "en": "Uzbekistan's student-voice platform: verified reviews and rankings of universities, a 52k+ phone-verified Telegram audience, admission cut-off scores for 75 universities (2020–2025).",
        },
        "description_rich": {
            "xo": (
                "<p><strong>EduStats</strong> (edustats.uz) — O'zbekiston talabalar fikri va ta'lim analitikasi "
                "platformasi: talabala universitet va o'qituvchilarni ochiq baholaydi, reyting halol qoladi — "
                "pul ko'rinishni sotib olishi mumkin, ballni hech qachon.</p>"
                "<p>Ekotizim web platforma + <strong>@TalabaOvvoziBot</strong>'dan iborat — 52k+ telefon-tasdiqlangan "
                "auditoriya. Haftalik TOP fikrla kanalga avtomatik chiqadi, AI sentiment tahlili fikrlarni signalga "
                "aylantiradi, 75 OTM o'tish ballari (2020–2025) esa qabul mavsumida trafik magniti.</p>"
            ),
            "uz": (
                "<p><strong>EduStats</strong> (edustats.uz) — O'zbekiston talabalar fikri va ta'lim analitikasi "
                "platformasi: talabalar universitet va o'qituvchilarni ochiq baholaydi, reyting halol qoladi — "
                "pul ko'rinishni sotib olishi mumkin, ballni hech qachon.</p>"
                "<p>Ekotizim web platforma + <strong>@TalabaOvvoziBot</strong>'dan iborat — 52k+ telefon-tasdiqlangan "
                "auditoriya. Haftalik TOP fikrlar kanalga avtomatik chiqadi, AI sentiment tahlili fikrlarni signalga "
                "aylantiradi, 75 OTM o'tish ballari (2020–2025) esa qabul mavsumida trafik magniti.</p>"
            ),
            "ru": (
                "<p><strong>EduStats</strong> (edustats.uz) — платформа студенческого мнения и образовательной "
                "аналитики Узбекистана: студенты открыто оценивают университеты и преподавателей, рейтинг остаётся "
                "честным — деньги могут купить видимость, но никогда — баллы.</p>"
                "<p>Экосистема = веб-платформа + <strong>@TalabaOvvoziBot</strong> — 52k+ телефон-верифицированная "
                "аудитория. Еженедельные TOP-отзывы публикуются в канал автоматически, AI-анализ тональности "
                "превращает отзывы в сигналы, а проходные баллы 75 вузов (2020–2025) — магнит трафика в сезон "
                "поступления.</p>"
            ),
            "en": (
                "<p><strong>EduStats</strong> (edustats.uz) is Uzbekistan's student-voice and education-analytics "
                "platform: students rate universities and faculty openly, and the ranking stays honest — money can "
                "buy visibility, never scores.</p>"
                "<p>The ecosystem pairs the web platform with <strong>@TalabaOvvoziBot</strong> — a 52k+ "
                "phone-verified Telegram audience. Weekly TOP insights auto-publish to the channel, AI sentiment "
                "analysis turns raw opinions into signals, and cut-off scores for 75 universities (2020–2025) make "
                "it a traffic magnet in admission season.</p>"
            ),
        },
    },
]

SKILLS = ["AI Product Strategy", "EdTech", "Education Analytics", "Testing Platforms", "AI Mentors", "Django", "Flutter"]

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
    help = "Create/update UzExam and EduStats as featured EdTech projects."

    @transaction.atomic
    def handle(self, *args, **options):
        from portfolio.models import Project, Skill

        skills = []
        for i, name in enumerate(SKILLS, start=1):
            skill, _ = Skill.objects.get_or_create(name=name, defaults={"category": "architecture", "order": i})
            skills.append(skill)

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
            project.technologies.set(skills)
            self.stdout.write(self.style.SUCCESS(f"Updated project: {project.slug}"))

        hidden = Project.objects.filter(slug__in=HIDE_SLUGS, is_visible=True).update(
            is_visible=False, is_featured=False
        )
        if hidden:
            self.stdout.write(self.style.SUCCESS(
                f"Hidden {hidden} legacy project card(s): {', '.join(HIDE_SLUGS)} (folded into EduStats)."
            ))
