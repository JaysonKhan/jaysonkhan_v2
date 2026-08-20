"""
Tests for blog Markdown rendering, contact spam protection, and core model integrity.
Run with: python manage.py test
"""
import shutil
import tempfile

from blog.templatetags.markdown_extras import render_markdown
from contact.spam_protection import (
    RATE_LIMIT_MAX_SUBMISSIONS,
    is_honeypot_filled,
    is_rate_limited,
)
from core.models import SiteSettings
from django.core.cache import cache
from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings

# Image-upload tests must not write into the developer's real media/ tree.
_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='jk-test-media-')


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
        request = self.factory.post('/contact/', {'name': 'Test', 'referral_code': ''})
        self.assertFalse(is_honeypot_filled(request))

    def test_filled_honeypot_blocked(self):
        """Request with filled honeypot is blocked."""
        request = self.factory.post('/contact/', {'name': 'Bot', 'referral_code': 'http://spam.com'})
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

    def test_footer_email_always_uses_main_email(self):
        """footer_email field was removed — footer_display_email is always the main email."""
        settings = SiteSettings.load()
        self.assertEqual(settings.footer_display_email, settings.email)

        settings.email = 'owner@example.com'
        self.assertEqual(settings.footer_display_email, 'owner@example.com')

    def test_footer_social_fallbacks(self):
        """Footer social URLs fall back to main social URLs."""
        settings = SiteSettings.load()

        # GitHub fallback
        settings.footer_social_github = ''
        self.assertEqual(settings.footer_display_github, settings.github_url)
        settings.footer_social_github = 'https://github.com/custom'
        self.assertEqual(settings.footer_display_github, 'https://github.com/custom')


class BioPageSeoTest(TestCase):
    """`/about/` — the person-entity page that name queries have to land on.

    These assertions are the SEO contract: if a refactor drops the legal name
    from the title/H1, or breaks the JSON-LD, the page silently stops doing
    the one job it exists for.
    """

    LEGAL_NAME = "Jahongir Qo'ziboyev"

    def setUp(self):
        cache.clear()  # sitemap views are cache_page'd — see GallerySitemapTest

    def _text(self, path):
        """Response body with entities resolved — Django escapes the apostrophe
        in "Qo'ziboyev" to &#x27;, which search engines unescape but a naive
        substring assertion would not."""
        import html as html_mod

        return html_mod.unescape(self.client.get(path).content.decode())

    def test_renders_in_every_language(self):
        for lang in ('xo', 'uz', 'ru', 'en'):
            with self.subTest(lang=lang):
                resp = self.client.get(f'/{lang}/about/')
                self.assertEqual(resp.status_code, 200)

    def test_legal_name_in_title_and_h1(self):
        """Latin locales spell it Latin, ru spells it Cyrillic — both must match
        what the corresponding search query looks like."""
        expected = {
            'xo': self.LEGAL_NAME,
            'uz': self.LEGAL_NAME,
            'ru': 'Жахонгир Кузибоев',
            'en': self.LEGAL_NAME,
        }
        for lang, name in expected.items():
            with self.subTest(lang=lang):
                body = self._text(f'/{lang}/about/')
                title = body.split('<title>')[1].split('</title>')[0]
                h1 = body.split('<h1')[1].split('</h1>')[0]
                self.assertIn(name, title)
                self.assertIn(name, h1)

    def test_meta_descriptions_fit_the_google_snippet(self):
        from presentation.web.bio_copy import BIO

        for lang, block in BIO.items():
            with self.subTest(lang=lang):
                self.assertLessEqual(len(block['meta_description']), 160)

    def test_structured_data_is_valid_json(self):
        """The @graph is hand-assembled in the template — one stray comma and
        every rich result on the page dies silently."""
        import json

        html = self.client.get('/uz/about/').content.decode()
        raw = html.split('<script type="application/ld+json">')[1].split('</script>')[0]
        graph = json.loads(raw)['@graph']
        types = [node['@type'] for node in graph]
        for expected in ('Person', 'ProfilePage', 'BreadcrumbList', 'FAQPage'):
            self.assertIn(expected, types)

    def test_profilepage_points_at_the_site_person_node(self):
        """A second Person node would split the entity in Google's index."""
        import json

        html = self.client.get('/en/about/').content.decode()
        raw = html.split('<script type="application/ld+json">')[1].split('</script>')[0]
        graph = json.loads(raw)['@graph']
        person = next(n for n in graph if n['@type'] == 'Person')
        profile = next(n for n in graph if n['@type'] == 'ProfilePage')
        self.assertEqual(profile['mainEntity']['@id'], person['@id'])
        self.assertEqual(len([n for n in graph if n['@type'] == 'Person']), 1)

    def test_name_variants_cover_all_three_scripts(self):
        """Latin, Uzbek Cyrillic and Russian Cyrillic spellings must all be on
        the page — that is the whole point of the disambiguation block."""
        body = self._text('/uz/about/')
        # Assert against <main> only: Person.alternateName in the JSON-LD head
        # already lists every spelling, so checking the raw body would pass even
        # if the visible disambiguation section disappeared.
        visible = body.split('<main>')[1].split('</main>')[0]
        for variant in (self.LEGAL_NAME, 'Жаҳонгир Қўзибоев', 'Жахонгир Кузибоев', 'Jayson Khan'):
            with self.subTest(variant=variant):
                self.assertIn(variant, visible)

    def test_linked_from_homepage_and_listed_in_sitemap(self):
        """An orphan page does not get crawled."""
        from django.urls import reverse

        about_url = reverse('about')
        self.assertIn(about_url, self.client.get(reverse('home')).content.decode())
        self.assertIn('/about/', self.client.get('/sitemap-static.xml').content.decode())


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class GallerySitemapTest(TestCase):
    """Gallery wall frames must reach Google Images.

    Only the first page of frames is server-rendered; the rest arrive over the
    JS feed, which crawlers never call. The homepage sitemap entry is therefore
    the only discovery path — if it regresses, the wall silently drops out of
    image search.
    """

    NS = {
        's': 'http://www.sitemaps.org/schemas/sitemap/0.9',
        'image': 'http://www.google.com/schemas/sitemap-image/1.1',
    }

    def setUp(self):
        # The sitemap views are cache_page'd. Any earlier test that fetched a
        # sitemap leaves a gallery-less copy in LocMemCache, and these tests
        # then assert against it — green alone, red in the full suite.
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from portfolio.models import GalleryImage

        # 1x1 GIF — enough for ImageField, no Pillow decode of a real photo.
        gif = (b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00'
               b'\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        # `hint` is a modeltranslation field: assigning the bare name writes
        # only the column for whatever language happens to be active, which
        # differs between a standalone run and the full suite. Set all four.
        cls.frame = GalleryImage.objects.create(
            image=SimpleUploadedFile('frame.gif', gif, content_type='image/gif'),
            cover=SimpleUploadedFile('frame-cover.gif', gif, content_type='image/gif'),
            hint='Xiva — Ichan-Qalʻa',
            hint_xo='Xiva — Ichan-Qalʻa',
            hint_uz='Xiva — Ichan-Qalʻa',
            hint_ru='Хива — Ичан-Кала',
            hint_en='Khiva — Itchan Kala',
        )
        GalleryImage.objects.create(
            image=SimpleUploadedFile('hidden.gif', gif, content_type='image/gif'),
            hint='Hidden frame',
            is_visible=False,
        )

    def _home_entry(self):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(self.client.get('/sitemap-static.xml').content)
        for url in root.findall('s:url', self.NS):
            if url.find('s:loc', self.NS).text.rstrip('/').endswith('/xo'):
                return url
        self.fail('homepage entry missing from sitemap-static.xml')

    def test_visible_frames_are_listed_on_the_homepage_entry(self):
        locs = [e.text for e in self._home_entry().findall('.//image:loc', self.NS)]
        self.assertIn(f'https://jaysonkhan.com{self.frame.image.url}', locs)
        self.assertIn(f'https://jaysonkhan.com{self.frame.cover.url}', locs)

    def test_hidden_frames_are_not_listed(self):
        locs = [e.text for e in self._home_entry().findall('.//image:loc', self.NS)]
        self.assertFalse([loc for loc in locs if 'hidden' in loc])

    def test_captions_carry_the_hint_and_the_owner_name(self):
        caps = [e.text for e in self._home_entry().findall('.//image:caption', self.NS)]
        match = [c for c in caps if 'Ichan' in c]
        self.assertTrue(match, 'gallery hint missing from captions')
        self.assertIn("Jahongir Qo'ziboyev", match[0])

    def test_other_static_pages_carry_no_images(self):
        """Only the homepage owns the wall — a stray image block elsewhere would
        tell Google the same photos live on five different URLs."""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(self.client.get('/sitemap-static.xml').content)
        for url in root.findall('s:url', self.NS):
            loc = url.find('s:loc', self.NS).text
            if loc.rstrip('/').endswith('/xo'):
                continue
            with self.subTest(loc=loc):
                self.assertEqual(url.findall('.//image:loc', self.NS), [])

    def test_project_and_post_sitemaps_still_emit_their_single_image(self):
        """The mixin moved from one image to a list — the older sitemaps must
        keep working."""
        import xml.etree.ElementTree as ET

        from django.core.files.uploadedfile import SimpleUploadedFile
        from portfolio.models import Project

        gif = (b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00'
               b'\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        Project.objects.create(
            title='Sitemap probe', slug='sitemap-probe',
            short_description='short',
            image=SimpleUploadedFile('proj.gif', gif, content_type='image/gif'),
            is_visible=True,
        )
        root = ET.fromstring(self.client.get('/sitemap-projects.xml').content)
        locs = [e.text for e in root.findall('.//image:loc', self.NS)]
        self.assertEqual(len(locs), 1)
        self.assertIn('proj', locs[0])
