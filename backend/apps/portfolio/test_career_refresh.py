from datetime import date
from importlib import import_module
from io import StringIO
from types import SimpleNamespace

from django.apps import apps
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from core.models import SiteSettings
from portfolio.models import Experience


class CareerRefreshTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_refresh_is_repeatable_and_preserves_existing_dialect_and_assets(self):
        Experience.objects.all().delete()
        old = Experience.objects.create(
            company="UIC Group", company_xo="UIC Group",
            position_xo="Owner's original title", description_xo="Owner's original wording",
            company_logo="experience/uic.png", company_url="https://uicgroup.uz",
            start_date=date(2024, 11, 1), is_current=True,
        )
        settings = SiteSettings.load()
        settings.about_description_xo = "Owner's original introduction"
        settings.save()
        refresh = import_module("portfolio.migrations.0023_refresh_confirmed_career").refresh_career
        for _ in range(2):
            refresh(apps, SimpleNamespace(connection=connection))
            call_command("apply_edtech_founder_copy", stdout=StringIO())

        old.refresh_from_db()
        settings.refresh_from_db()
        self.assertEqual(Experience.objects.count(), 5)
        self.assertEqual(old.start_date, date(2023, 9, 1))
        self.assertEqual(old.end_date, date(2025, 12, 31))
        self.assertFalse(old.is_current)
        self.assertEqual(old.position_xo, "Owner's original title")
        self.assertEqual(old.description_xo, "Owner's original wording")
        self.assertEqual(old.company_logo.name, "experience/uic.png")
        self.assertEqual(old.company_url, "https://uicgroup.uz")
        self.assertEqual(settings.about_description_xo, "Owner's original introduction")
        current = Experience.objects.get(company_en="Consort Group LLC")
        self.assertEqual(current.start_date, date(2026, 6, 1))
        self.assertTrue(current.is_current)
        self.assertEqual(current.position_en, "Voice AI Engineer")
        self.assertIn("voice AI agronomist", current.description_en)
        aiba = Experience.objects.get(company_en="AI Business Assistant (AIBA)")
        self.assertEqual(aiba.end_date, date(2025, 11, 30))

    def test_voice_ai_resumes_are_downloadable_on_home_and_about_in_all_locales(self):
        settings = SiteSettings.load()
        settings.about_title_en = "About me"
        settings.about_title_xo = "Man haqimda"
        settings.resume_file = ""  # Downloads do not require an admin upload.
        settings.save()
        for lang in ("xo", "uz", "ru", "en"):
            for page in ("", "about/"):
                with self.subTest(lang=lang, page=page):
                    response = self.client.get(f"/{lang}/{page}")
                    self.assertEqual(response.status_code, 200)
                    for lang_code in ("en", "ru"):
                        path = f"resumes/jahongir-kuziboev-voice-ai-engineer-{lang_code}.pdf"
                        self.assertContains(response, f'href="/static/{path}" download=')
                        with open(finders.find(path), "rb") as pdf:
                            self.assertEqual(pdf.read(5), b"%PDF-")

    def test_xo_fact_refresh_changes_only_the_figures(self):
        settings = SiteSettings.load()
        settings.about_description_xo = "Man quraman. 85k+ ochiq savol va 21k+ foydalanuvchi, 53k+ auditoriya."
        settings.save()
        Experience.objects.all().delete()
        row = Experience.objects.create(
            company="UzExam.uz", description_xo="85k+ ochiq savol, 193 faol OTM va 121 OTM.",
            start_date=date(2026, 4, 1), is_current=True,
        )
        migration = import_module("portfolio.migrations.0024_refresh_xo_product_facts")
        for _ in range(2):  # repeatable
            migration.refresh_facts(apps, SimpleNamespace(connection=connection))
        settings.refresh_from_db()
        row.refresh_from_db()
        self.assertEqual(settings.about_description_xo,
                         "Man quraman. 167k+ ochiq savol va 39k+ foydalanuvchi, 54k+ auditoriya.")
        self.assertEqual(row.description_xo, "167k+ ochiq savol, 208 faol OTM va 126 OTM.")

    def test_voice_ai_title_refresh_swaps_only_role_wording(self):
        settings = SiteSettings.load()
        settings.about_description_xo = ("Man Jayson Khan — Xorazmdan chiqqan AI, mobil va full-stack dasturchi, "
                                         "AI EdTech founder.")
        settings.hero_eyebrow_xo = "AI · Mobil · Full-stack dasturchi · UzExam · EduStats · O'zbekiston"
        settings.save()
        Experience.objects.all().delete()
        consort = Experience.objects.create(
            company="Consort Group LLC", position_xo="Mobile Developer", position_en="Mobile Developer",
            start_date=date(2026, 6, 1), is_current=True,
        )
        uic = Experience.objects.create(
            company="UIC Group", position_xo="Flutter Mobile Engineer", start_date=date(2023, 9, 1),
        )
        custom = Experience.objects.create(
            company="AI Business Assistant (AIBA)", position_xo="Mobile Team Lead — AI Business Assistant",
            start_date=date(2025, 8, 1),
        )
        migration = import_module("portfolio.migrations.0025_voice_ai_engineer_titles")
        for _ in range(2):  # repeatable
            migration.refresh_titles(apps, SimpleNamespace(connection=connection))
        settings.refresh_from_db()
        for row in (consort, uic, custom):
            row.refresh_from_db()
        self.assertEqual(settings.about_description_xo,
                         "Man Jayson Khan — Xorazmdan chiqqan Voice AI Engineer, AI EdTech founder.")
        self.assertEqual(settings.hero_eyebrow_xo, "Voice AI Engineer · UzExam · EduStats · O'zbekiston")
        self.assertEqual((consort.position_xo, consort.position_en), ("Voice AI Engineer", "Voice AI Engineer"))
        self.assertEqual(uic.position_xo, "Software Engineer")
        self.assertEqual(custom.position_xo, "Mobile Team Lead — AI Business Assistant")
