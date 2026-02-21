"""
Tests for blog Markdown rendering, contact spam protection, and core model integrity.
Run with: python manage.py test
"""
from django.test import TestCase, RequestFactory
from django.template import Template, Context
from unittest.mock import patch

from blog.templatetags.markdown_extras import render_markdown
from contact.spam_protection import is_honeypot_filled, is_rate_limited, RATE_LIMIT_MAX_SUBMISSIONS
from core.models import SiteSettings


class MarkdownRenderingTest(TestCase):
    """Test the render_markdown template filter."""

    def test_basic_markdown(self):
        """Bold, italic, links are rendered."""
        result = render_markdown("**bold** and *italic*")
        self.assertIn('<strong>bold</strong>', result)
        self.assertIn('<em>italic</em>', result)

    def test_empty_input(self):
        """Empty string returns empty string."""
        self.assertEqual(render_markdown(''), '')
        self.assertEqual(render_markdown(None), '')

    def test_script_tag_stripped(self):
        """XSS via script tags is sanitized."""
        result = render_markdown('<script>alert("xss")</script>Hello')
        self.assertNotIn('<script>', result)
        self.assertIn('Hello', result)

    def test_fenced_code_blocks(self):
        """Fenced code blocks are rendered."""
        md = '```python\nprint("hello")\n```'
        result = render_markdown(md)
        self.assertIn('<code', result)

    def test_links_rendered(self):
        """Links are rendered with href."""
        result = render_markdown('[Google](https://google.com)')
        self.assertIn('href="https://google.com"', result)

    def test_template_filter_integration(self):
        """The filter can be used in Django templates."""
        template = Template('{% load markdown_extras %}{{ content|render_markdown }}')
        context = Context({'content': '**hello** world'})
        rendered = template.render(context)
        self.assertIn('<strong>hello</strong>', rendered)


class HoneypotTest(TestCase):
    """Test honeypot spam detection."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_empty_honeypot_passes(self):
        """Normal request without honeypot value passes."""
        request = self.factory.post('/contact/', {'name': 'Test', 'website': ''})
        self.assertFalse(is_honeypot_filled(request))

    def test_filled_honeypot_blocked(self):
        """Request with filled honeypot is blocked."""
        request = self.factory.post('/contact/', {'name': 'Bot', 'website': 'http://spam.com'})
        self.assertTrue(is_honeypot_filled(request))

    def test_missing_honeypot_passes(self):
        """Request without honeypot field at all passes (graceful fallback)."""
        request = self.factory.post('/contact/', {'name': 'Test'})
        self.assertFalse(is_honeypot_filled(request))


class RateLimitTest(TestCase):
    """Test rate limiting for contact form submissions."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_first_request_allowed(self):
        """First request from an IP is allowed."""
        request = self.factory.post('/contact/', REMOTE_ADDR='192.168.1.100')
        self.assertFalse(is_rate_limited(request))

    def test_exceeding_limit_blocked(self):
        """Requests exceeding the limit are blocked."""
        for i in range(RATE_LIMIT_MAX_SUBMISSIONS):
            request = self.factory.post('/contact/', REMOTE_ADDR='10.0.0.50')
            self.assertFalse(is_rate_limited(request))

        # Next request should be blocked
        request = self.factory.post('/contact/', REMOTE_ADDR='10.0.0.50')
        self.assertTrue(is_rate_limited(request))

    def test_different_ips_independent(self):
        """Rate limits are per-IP."""
        for i in range(RATE_LIMIT_MAX_SUBMISSIONS):
            request = self.factory.post('/contact/', REMOTE_ADDR='10.0.0.1')
            is_rate_limited(request)

        # Different IP should still be allowed
        request = self.factory.post('/contact/', REMOTE_ADDR='10.0.0.2')
        self.assertFalse(is_rate_limited(request))


class SiteSettingsModelTest(TestCase):
    """Test SiteSettings singleton and fallback properties."""

    def test_singleton_load(self):
        """SiteSettings.load() creates and returns a singleton."""
        settings = SiteSettings.load()
        self.assertIsNotNone(settings)
        self.assertEqual(settings.pk, 1)

    def test_singleton_prevents_duplicate(self):
        """Creating a second SiteSettings raises ValidationError."""
        SiteSettings.load()  # ensure pk=1 exists
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            SiteSettings(pk=None).save()

    def test_logo_text_fallback(self):
        """display_logo_text falls back to site_author when logo_text is empty."""
        settings = SiteSettings.load()
        settings.logo_text = ''
        self.assertEqual(settings.display_logo_text, settings.site_author)

        settings.logo_text = 'Custom Logo'
        self.assertEqual(settings.display_logo_text, 'Custom Logo')

    def test_footer_description_fallback(self):
        """footer_display_description falls back to site_tagline."""
        settings = SiteSettings.load()
        settings.footer_description = ''
        self.assertEqual(settings.footer_display_description, settings.site_tagline)

        settings.footer_description = 'Custom footer desc'
        self.assertEqual(settings.footer_display_description, 'Custom footer desc')

    def test_footer_email_fallback(self):
        """footer_display_email falls back to main email."""
        settings = SiteSettings.load()
        settings.footer_email = ''
        self.assertEqual(settings.footer_display_email, settings.email)

        settings.footer_email = 'footer@example.com'
        self.assertEqual(settings.footer_display_email, 'footer@example.com')

    def test_footer_social_fallbacks(self):
        """Footer social URLs fall back to main social URLs."""
        settings = SiteSettings.load()

        # GitHub fallback
        settings.footer_social_github = ''
        self.assertEqual(settings.footer_display_github, settings.github_url)
        settings.footer_social_github = 'https://github.com/custom'
        self.assertEqual(settings.footer_display_github, 'https://github.com/custom')
