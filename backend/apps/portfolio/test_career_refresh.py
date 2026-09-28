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
        self.assertIn("Growz and Bizon", current.description_en)
        aiba = Experience.objects.get(company_en="AI Business Assistant (AIBA)")
        self.assertEqual(aiba.end_date, date(2025, 11, 30))

    def test_both_english_resumes_are_downloadable_on_home_and_about_in_all_locales(self):
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
                    for role in ("software-engineer", "mobile-developer"):
                        path = f"resumes/jahongir-kuziboev-{role}-en.pdf"
                        self.assertContains(response, f'href="/static/{path}" download=')
                        with open(finders.find(path), "rb") as pdf:
                            self.assertEqual(pdf.read(5), b"%PDF-")
