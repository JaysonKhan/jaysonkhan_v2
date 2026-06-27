"""Create/update key EdTech projects for jaysonkhan.com."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

LANGS = ("xo", "uz", "ru", "en")

PROJECTS = [
    {
        "slug": "uzexam",
        "web_page_url": "https://uzexam.uz/",
        "order": -100,
        "stats": [{"v": "40k+", "l": "questions"}, {"v": "AI", "l": "mentor"}, {"v": "DTM", "l": "mock"}],
        "title": {
            "xo": "UzExam — AI bilan kuchaytirilgan test platforma",
            "uz": "UzExam — AI bilan kuchaytirilgan test platforma",
            "ru": "UzExam — AI-усиленная тестовая платформа",
            "en": "UzExam — AI-powered testing platform",
        },
        "short_description": {
            "xo": "DTM, IELTS, SAT va universitet tayyorgarligi uchun test, mock, xatolarni qaytarish va progress analitikasi.",
            "uz": "DTM, IELTS, SAT va universitet tayyorgarligi uchun test, mock, xatolarni qaytarish va progress analitikasi.",
            "ru": "Тесты, mock exams, повтор ошибок и аналитика прогресса для DTM, IELTS, SAT и поступления.",
            "en": "Tests, mock exams, mistake repetition and progress analytics for DTM, IELTS, SAT and university prep.",
        },
        "description_rich": {
            "xo": "<p><strong>UzExam</strong> — O'zbekistonda abituriyentlar va o'quvchilar uchun AI yordamida kuchaytirilayotgan test platforma. Mahsulot savollar bazasi, mock testlar, xatolarni qaytarish, statistika va kelajakdagi AI mentor tajribasini bitta ekotizimga yig'adi.</p>",
            "uz": "<p><strong>UzExam</strong> — O'zbekistonda abituriyentlar va o'quvchilar uchun AI yordamida kuchaytirilayotgan test platforma. Mahsulot savollar bazasi, mock testlar, xatolarni qaytarish, statistika va kelajakdagi AI mentor tajribasini bitta ekotizimga yig'adi.</p>",
            "ru": "<p><strong>UzExam</strong> — AI-усиленная тестовая платформа для абитуриентов и студентов в Узбекистане. Продукт объединяет базу вопросов, mock exams, повтор ошибок, статистику и будущий AI mentor опыт.</p>",
            "en": "<p><strong>UzExam</strong> is an AI-powered testing platform for students in Uzbekistan. It combines a question bank, mock exams, mistake repetition, progress statistics and a future AI mentor experience.</p>",
        },
    },
    {
        "slug": "edustats",
        "web_page_url": "https://edustats.uz/",
        "order": -90,
        "stats": [{"v": "Data", "l": "analytics"}, {"v": "AI", "l": "insights"}, {"v": "Edu", "l": "growth"}],
        "title": {
            "xo": "Edustats — ta'lim analitikasi platformasi",
            "uz": "Edustats — ta'lim analitikasi platformasi",
            "ru": "Edustats — платформа образовательной аналитики",
            "en": "Edustats — education analytics platform",
        },
        "short_description": {
            "xo": "O'quv natijalari, test statistikasi va ta'lim mahsulotlari uchun data-driven qarorlar platformasi.",
            "uz": "O'quv natijalari, test statistikasi va ta'lim mahsulotlari uchun data-driven qarorlar platformasi.",
            "ru": "Платформа для анализа результатов, тестовой статистики и data-driven решений в образовании.",
            "en": "A platform for learning outcomes, test statistics and data-driven decisions in education.",
        },
        "description_rich": {
            "xo": "<p><strong>Edustats</strong> — ta'limdagi natijalarni ko'rinadigan qiladigan analitika yo'nalishi. Maqsad: o'quvchi, ustoz va loyiha egasi uchun test natijalarini tushunarli data'ga aylantirish.</p>",
            "uz": "<p><strong>Edustats</strong> — ta'limdagi natijalarni ko'rinadigan qiladigan analitika yo'nalishi. Maqsad: o'quvchi, ustoz va loyiha egasi uchun test natijalarini tushunarli data'ga aylantirish.</p>",
            "ru": "<p><strong>Edustats</strong> делает образовательные результаты видимыми и превращает тестовые данные в понятную аналитику для студентов, преподавателей и product owners.</p>",
            "en": "<p><strong>Edustats</strong> makes learning outcomes visible and turns test data into clear analytics for students, teachers and product owners.</p>",
        },
    },
]

SKILLS = ["AI Product Strategy", "EdTech", "Education Analytics", "Testing Platforms", "AI Mentors", "Django", "Flutter"]


def set_translated(obj, field, values):
    for lang in LANGS:
        attr = f"{field}_{lang}"
        if hasattr(obj, attr):
            setattr(obj, attr, values[lang])
        elif lang == "xo" and hasattr(obj, field):
            setattr(obj, field, values[lang])


class Command(BaseCommand):
    help = "Create/update UzExam and Edustats as featured EdTech projects."

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
