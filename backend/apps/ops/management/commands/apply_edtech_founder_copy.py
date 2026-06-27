"""Apply jaysonkhan.com AI EdTech founder positioning.

Idempotent production command. Keeps `xo` as the default Khorezm dialect locale,
updates the SiteSettings singleton in all four locales (xo, uz, ru, en), and
rewrites any legacy "VibeCoder" Experience-timeline title to the AI EdTech wording.
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
        "xo": "AI yordamida EdTech mahsulotlar, test platformalari va ta'lim analitikasini quramiz.",
        "uz": "AI yordamida EdTech mahsulotlar, test platformalari va ta'lim analitikasini quramiz.",
        "ru": "AI-продукты для EdTech: тестовые платформы, образовательная аналитика и автоматизация.",
        "en": "AI-powered EdTech products, testing platforms and education analytics for Uzbekistan.",
    },
    "meta_description": {
        "xo": "Jayson Khan — UzExam va Edustats asoschisi. O'zbekistonda AI yordamida test platformalari, ta'lim analitikasi va EdTech mahsulotlar quradi.",
        "uz": "Jayson Khan — UzExam va Edustats asoschisi. O'zbekistonda AI yordamida test platformalari, ta'lim analitikasi va EdTech mahsulotlar quradi.",
        "ru": "Jayson Khan — основатель UzExam и Edustats, AI EdTech специалист, создающий тестовые платформы и аналитику образования в Узбекистане.",
        "en": "Jayson Khan is an AI EdTech specialist and founder of UzExam and Edustats, building testing platforms and education analytics in Uzbekistan.",
    },
    "meta_keywords": {
        "xo": "Jayson Khan, JaysonKhan, Jahongir Qo'ziboyev, Qo'ziboyev Jahongir, Kuziboyev Jahongir, AI EdTech Uzbekistan, UzExam asoschisi, Edustats, test platforma O'zbekiston, ta'lim analitikasi, AI mentor, sun'iy intellekt mutaxassis O'zbekiston",
        "uz": "Jayson Khan, JaysonKhan, Jahongir Qo'ziboyev, Qo'ziboyev Jahongir, Kuziboyev Jahongir, AI EdTech Uzbekistan, UzExam asoschisi, Edustats, test platforma O'zbekiston, ta'lim analitikasi, AI mentor, sun'iy intellekt mutaxassis O'zbekiston",
        "ru": "Jayson Khan, JaysonKhan, Жахонгир Кузибоев, Кузибоев Жахонгир, Джахонгир Кузибоев, AI EdTech Узбекистан, основатель UzExam, Edustats, тестовая платформа, образовательная аналитика, AI mentor, AI специалист Узбекистан",
        "en": "Jayson Khan, JaysonKhan, Jahongir Qoziboyev, Qoziboyev Jahongir, Kuziboyev Jahongir, AI EdTech Uzbekistan, UzExam founder, Edustats, test platform Uzbekistan, education analytics, AI mentor, AI specialist Uzbekistan",
    },
    "hero_eyebrow": {
        "xo": "AI EdTech · UzExam · Edustats · O'zbekiston",
        "uz": "AI EdTech · UzExam · Edustats · O'zbekiston",
        "ru": "AI EdTech · UzExam · Edustats · Узбекистан",
        "en": "AI EdTech · UzExam · Edustats · Uzbekistan",
    },
    "hero_title": {
        "xo": "O'zbekistonda AI asosidagi<br>EdTech mahsulotlar",
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
        "xo": "Man Jayson Khan — UzExam va Edustats asoschisiman. Test platformalari, AI mentorlar, ta'lim analitikasi va o'quvchilar uchun real foyda beradigan raqamli mahsulotlar quraman.",
        "uz": "Men Jayson Khan — UzExam va Edustats asoschisiman. Test platformalari, AI mentorlar, ta'lim analitikasi va o'quvchilar uchun real foyda beradigan raqamli mahsulotlar quraman.",
        "ru": "Я Jayson Khan — основатель UzExam и Edustats. Строю тестовые платформы, AI-менторов, образовательную аналитику и продукты, которые реально помогают студентам.",
        "en": "I'm Jayson Khan — founder of UzExam and Edustats. I build testing platforms, AI mentors, education analytics and practical learning products for Uzbekistan.",
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
        "xo": "Man Jayson Khan — O'zbekistonda ta'lim mahsulotlari, test tizimlari va AI yordamidagi o'quv tajribalarini qurayotgan founder/operator. Asosiy fokusim: UzExam, Edustats, AI mentorlar va o'quvchilar progressini aniq ko'rsatadigan analitika.",
        "uz": "Men Jayson Khan — O'zbekistonda ta'lim mahsulotlari, test tizimlari va AI yordamidagi o'quv tajribalarini qurayotgan founder/operator. Asosiy fokusim: UzExam, Edustats, AI mentorlar va o'quvchilar progressini aniq ko'rsatadigan analitika.",
        "ru": "Я Jayson Khan — founder/operator, который строит образовательные продукты, тестовые системы и AI-опыт обучения в Узбекистане. Основной фокус: UzExam, Edustats, AI-менторы и аналитика прогресса студентов.",
        "en": "I'm Jayson Khan — a founder/operator building education products, testing systems and AI-assisted learning experiences in Uzbekistan. My focus is UzExam, Edustats, AI mentors and student progress analytics.",
    },
    "featured_projects_title": {
        "xo": "AI EdTech ekotizimidagi asosiy mahsulotlar.",
        "uz": "AI EdTech ekotizimidagi asosiy mahsulotlar.",
        "ru": "Ключевые продукты AI EdTech экосистемы.",
        "en": "Core products in the AI EdTech ecosystem.",
    },
    "projects_page_title": {
        "xo": "AI EdTech loyihalar.",
        "uz": "AI EdTech loyihalar.",
        "ru": "AI EdTech проекты.",
        "en": "AI EdTech Projects.",
    },
    "projects_page_subtitle": {
        "xo": "UzExam, Edustats, AI mentorlar, test platformalari va ta'lim analitikasi bo'yicha mahsulotlar.",
        "uz": "UzExam, Edustats, AI mentorlar, test platformalari va ta'lim analitikasi bo'yicha mahsulotlar.",
        "ru": "UzExam, Edustats, AI-менторы, тестовые платформы и продукты образовательной аналитики.",
        "en": "UzExam, Edustats, AI mentors, testing platforms and education analytics products.",
    },
    "blog_page_title": {
        "xo": "AI EdTech jurnal.",
        "uz": "AI EdTech jurnal.",
        "ru": "AI EdTech журнал.",
        "en": "AI EdTech Journal.",
    },
    "blog_page_subtitle": {
        "xo": "AI, EdTech, test platformalari, product building va O'zbekistonda ta'lim mahsulotlari haqida yozuvlar.",
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
        "xo": "Test platforma, AI mentor, ta'lim analitikasi yoki EdTech growth bo'yicha yozing — Telegram eng tez kanal.",
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
        "xo": "Jayson Khan — UzExam va Edustats asoschisi. AI yordamida EdTech, test platformalari va ta'lim analitikasi quradi.",
        "uz": "Jayson Khan — UzExam va Edustats asoschisi. AI yordamida EdTech, test platformalari va ta'lim analitikasi quradi.",
        "ru": "Jayson Khan — основатель UzExam и Edustats. AI-продукты для EdTech, тестов и образовательной аналитики.",
        "en": "Jayson Khan — founder of UzExam and Edustats. Building AI-powered EdTech, testing platforms and education analytics.",
    },
}

PLAIN = {
    "site_author": "Jayson Khan",
    "site_author_initials": "JK",
    "logo_text": "Jayson Khan",
    "og_url": "https://jaysonkhan.com",
    "nav_cta_url": "/contact/",
    "hero_location": "Tashkent · Uzbekistan",
    "stat_1_count": 40,
    "stat_1_suffix": "k+",
    "stat_2_count": 2,
    "stat_2_suffix": "+",
    "stat_3_count": 1,
    "stat_3_suffix": "+",
    "stat_4_count": 100,
    "stat_4_suffix": "%",
}


def set_translated(obj, field, values):
    for lang in LANGS:
        attr = f"{field}_{lang}"
        if hasattr(obj, attr):
            setattr(obj, attr, values[lang])
        elif lang == "xo" and hasattr(obj, field):
            setattr(obj, field, values[lang])


class Command(BaseCommand):
    help = "Apply AI EdTech founder positioning to SiteSettings."

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

        # Rewrite legacy "VibeCoder" identity in Experience timeline rows.
        # position is a translated field → patch every language column present.
        from portfolio.models import Experience

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
