"""The Django side of the voice agent demo: the page, its call token and the menu link."""

import json
import re

from core.models import SiteSettings
from demos.voice_agent.tokens import verify_token
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

LANGS = ("xo", "uz", "ru", "en")


class VoiceAgentDemoPageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def config(self, html: str) -> dict:
        match = re.search(r'<script id="voice-config" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(match, "voice-config JSON is missing")
        return json.loads(match.group(1))

    def test_page_renders_in_every_language_with_a_valid_call_token(self):
        for lang in LANGS:
            with self.subTest(lang=lang), translation.override(lang):
                response = self.client.get(reverse("voice_agent_demo"))
                self.assertEqual(response.status_code, 200)
                config = self.config(response.content.decode())
                self.assertTrue(verify_token(settings.SECRET_KEY, config["token"]))
                self.assertIn("voice-agent-worklets", config["workletUrl"])
                self.assertEqual(set(config["text"]["errors"]), {
                    "mic_blocked", "closed", "bad_token", "busy", "ip_daily", "daily_budget", "time_up", "unavailable",
                })

    def test_strings_are_translated(self):
        with translation.override("ru"):
            html = self.client.get(reverse("voice_agent_demo")).content.decode()
        self.assertIn("Начать звонок", html)
        self.assertEqual(self.config(html)["text"]["listening"], "Слушает")

    def test_every_page_links_to_the_demo_from_the_menu(self):
        with translation.override("en"):
            html = self.client.get(reverse("about")).content.decode()
            demo_url = reverse("voice_agent_demo")
        self.assertEqual(demo_url, "/en/demos/voice-agent/")
        self.assertEqual(html.count(f'href="{demo_url}"'), 2)  # desktop menu + mobile menu

    def test_only_the_demo_page_may_use_the_microphone(self):
        with translation.override("en"):
            demo = self.client.get(reverse("voice_agent_demo"))
            about = self.client.get(reverse("about"))
        self.assertIn("microphone=(self)", demo["Permissions-Policy"])
        self.assertIn("microphone=()", about["Permissions-Policy"])
