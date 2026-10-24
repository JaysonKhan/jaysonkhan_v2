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

    def test_portrait_cover_reveals_original_and_comments_do_not_leak(self):
        settings = SiteSettings.objects.first() or SiteSettings.objects.create()
        settings.about_image = "about/original.png"
        settings.about_image_anime = "about/anime.jpg"
        settings.save()
        for lang in ("xo", "uz", "ru", "en"):
            with self.subTest(lang=lang):
                response = self.client.get(f"/{lang}/about/")
                self.assertContains(response, 'src="/media/about/anime.jpg"')
                self.assertContains(response, 'data-full="/media/about/original.png"')
                self.assertContains(response, 'href="/media/about/original.png"')
                self.assertContains(response, "js/lightbox.js")
                self.assertNotContains(response, "{#")
                self.assertNotContains(response, "#}")

    def test_portrait_fallback_without_anime(self):
        settings = SiteSettings.objects.first() or SiteSettings.objects.create()
        settings.about_image = "about/original.png"
        settings.about_image_anime = ""
        settings.save()
        self.assertContains(self.client.get("/en/about/"), 'src="/media/about/original.png"')

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
        tell Google the same photos live on five different URLs. (The four
        locale entries of the homepage are the same page and all carry it.)"""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(self.client.get('/sitemap-static.xml').content)
        for url in root.findall('s:url', self.NS):
            loc = url.find('s:loc', self.NS).text
            if loc.rstrip('/').endswith(('/xo', '/uz', '/ru', '/en')):
                continue
            with self.subTest(loc=loc):
                self.assertEqual(url.findall('.//image:loc', self.NS), [])

    def test_project_and_post_sitemaps_still_emit_their_single_image(self):
        """The mixin moved from one image to a list — the older sitemaps must
        keep working: exactly one image, on each locale's entry."""
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
        urls = root.findall('s:url', self.NS)
        self.assertEqual(len(urls), 4)  # one <url> per locale
        for url in urls:
            locs = [e.text for e in url.findall('.//image:loc', self.NS)]
            self.assertEqual(len(locs), 1)
            self.assertIn('proj', locs[0])


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class SitemapI18nTest(TestCase):
    """Every locale is its own <url>, and the XML is the same for every
    requester.

    Before 2026-10-25 <loc> was built under the request's language, so a
    crawler sending Accept-Language: en got 13 /en/ URLs out of 52 — and
    cache_page then served that copy to everyone with the same header.
    """

    NS = GallerySitemapTest.NS
    LANGS = ('xo', 'uz', 'ru', 'en')
    GIF = (b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00'
           b'\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')

    def setUp(self):
        cache.clear()  # sitemap views are cache_page'd — see GallerySitemapTest

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def _urls(self, path, **extra):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(self.client.get(path, **extra).content)
        return root.findall('s:url', self.NS)

    def _locs(self, path, **extra):
        return [u.find('s:loc', self.NS).text for u in self._urls(path, **extra)]

    def test_static_sitemap_lists_every_locale(self):
        from core.sitemaps import StaticSitemap

        # An English requester still gets all four locales.
        locs = self._locs('/sitemap-static.xml', HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(len(locs), len(StaticSitemap.PAGES) * len(self.LANGS))
        for lang in self.LANGS:
            with self.subTest(lang=lang):
                self.assertIn(f'https://testserver/{lang}/about/', locs)

    def test_project_and_post_sitemaps_list_every_locale(self):
        from blog.models import Post
        from django.contrib.auth import get_user_model
        from portfolio.models import Project

        Project.objects.create(title='Listed', slug='listed', is_visible=True)
        Project.objects.create(title='Hidden', slug='hidden', is_visible=False)
        author = get_user_model().objects.create_user(
            username='sitemap-author', email='sitemap@example.com', password='secret123')
        Post.objects.create(title='Listed', slug='listed', author=author, is_published=True)
        Post.objects.create(title='Draft', slug='draft', author=author, is_published=False)
        for section, path in (('projects', 'projects'), ('blog', 'blog')):
            with self.subTest(section=section):
                self.assertEqual(
                    sorted(self._locs(f'/sitemap-{section}.xml', HTTP_ACCEPT_LANGUAGE='ru')),
                    sorted(f'https://testserver/{lang}/{path}/listed/' for lang in self.LANGS),
                )

    def test_output_does_not_depend_on_accept_language(self):
        from datetime import datetime
        from datetime import timezone as dt_timezone
        from unittest import mock

        from django.core.files.uploadedfile import SimpleUploadedFile
        from portfolio.models import Project

        # Translated title → translated caption: the strongest place for a
        # request language to leak.
        Project.objects.create(
            title_xo='Loyiha', title_uz='Loyiha', title_ru='Проект', title_en='Project',
            slug='probe', is_visible=True,
            image=SimpleUploadedFile('probe.gif', self.GIF, content_type='image/gif'),
        )
        # StaticSitemap stamps lastmod with `now` — pin it so a second boundary
        # between two requests cannot fake a difference.
        fixed = datetime(2026, 10, 25, tzinfo=dt_timezone.utc)
        for section in ('static', 'projects'):
            with self.subTest(section=section), mock.patch('core.sitemaps._now', return_value=fixed):
                bodies = set()
                for lang in self.LANGS:
                    cache.clear()
                    bodies.add(self.client.get(f'/sitemap-{section}.xml', HTTP_ACCEPT_LANGUAGE=lang).content)
                self.assertEqual(len(bodies), 1)

    def test_captions_follow_the_entry_locale(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from portfolio.models import Project

        Project.objects.create(
            title_xo='Loyiha', title_uz='Loyiha', title_ru='Проект', title_en='Project',
            slug='probe', is_visible=True,
            image=SimpleUploadedFile('probe.gif', self.GIF, content_type='image/gif'),
        )
        expected = {'/ru/': 'Проект', '/en/': 'Project', '/uz/': 'Loyiha', '/xo/': 'Loyiha'}
        urls = self._urls('/sitemap-projects.xml', HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual(len(urls), 4)
        for url in urls:
            loc = url.find('s:loc', self.NS).text
            caption = url.find('.//image:caption', self.NS).text
            prefix = next(p for p in expected if p in loc)
            with self.subTest(loc=loc):
                self.assertIn(expected[prefix], caption)

    def test_hreflang_alternates_unchanged(self):
        """uz/ru/en siblings + x-default → /xo/ on every locale's entry. 'xo'
        is not an ISO code and stays out of hreflang (Ahrefs 2026-08-03)."""
        xhtml = {'xhtml': 'http://www.w3.org/1999/xhtml'}
        urls = self._urls('/sitemap-static.xml', HTTP_HOST='jaysonkhan.com')
        self.assertTrue(urls)
        for url in urls:
            loc = url.find('s:loc', self.NS).text
            with self.subTest(loc=loc):
                links = {link.get('hreflang'): link.get('href') for link in url.findall('xhtml:link', xhtml)}
                self.assertEqual(sorted(links), ['en', 'ru', 'uz', 'x-default'])
                path = loc.split('jaysonkhan.com/', 1)[1][3:]  # drop the "xo/" etc. prefix
                self.assertEqual(links['x-default'], f'https://jaysonkhan.com/xo/{path}')
                self.assertEqual(links['en'], f'https://jaysonkhan.com/en/{path}')


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class HeadMetaTest(TestCase):
    """base.html Open Graph + JSON-LD contract (technical audit 2026-10-25)."""

    GIF = (b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00'
           b'\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
    LANGS = ('xo', 'uz', 'ru', 'en')

    @classmethod
    def setUpTestData(cls):
        from blog.models import Post
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile
        from portfolio.models import Project

        settings = SiteSettings.objects.first() or SiteSettings.objects.create()
        settings.og_image = 'og/banner.png'
        settings.github_url = 'https://github.com/JaysonKhan'
        settings.linkedin_url = 'https://www.linkedin.com/in/jaysonkhan/'
        settings.telegram_url = 'https://t.me/jaysonkhan'
        settings.apps_section_visible = True
        settings.save()
        author = get_user_model().objects.create_user(
            username='og-author', email='og@example.com', password='secret123')
        cls.post = Post.objects.create(
            title='With image', slug='with-image', author=author, is_published=True,
            featured_image=SimpleUploadedFile('post.gif', cls.GIF, content_type='image/gif'))
        cls.bare_post = Post.objects.create(
            title='No image', slug='no-image', author=author, is_published=True)
        cls.project = Project.objects.create(
            title='With cover', slug='with-cover', is_visible=True,
            image=SimpleUploadedFile('cover.gif', cls.GIF, content_type='image/gif'))

    def setUp(self):
        cache.clear()  # SiteSettings is cached 5 min — start every test from the row above

    @classmethod
    def tearDownClass(cls):
        cache.clear()
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def _meta(self, html, attr, name):
        import re

        return re.findall(rf'<meta {attr}="{name}" content="([^"]*)"', html)

    def _graph(self, path):
        import json

        html = self.client.get(path).content.decode()
        raw = html.split('<script type="application/ld+json">')[1].split('</script>')[0]
        return json.loads(raw)['@graph']

    def test_og_url_is_the_current_localized_page(self):
        """Was hardcoded to the site root on every template except /about/."""
        for path in ('/xo/', '/en/blog/', '/uz/about/', f'/ru/projects/{self.project.slug}/'):
            with self.subTest(path=path):
                html = self.client.get(path).content.decode()
                self.assertEqual(self._meta(html, 'property', 'og:url'), [f'https://jaysonkhan.com{path}'])

    def test_detail_pages_emit_one_absolute_og_image(self):
        """Used to emit the generic banner AND a relative page image — two
        sets, the second invalid for OG."""
        for path in (self.post.get_absolute_url(), self.project.get_absolute_url()):
            with self.subTest(path=path):
                html = self.client.get(path).content.decode()
                og = self._meta(html, 'property', 'og:image')
                self.assertEqual(len(og), 1)
                self.assertEqual(og, self._meta(html, 'name', 'twitter:image'))
                self.assertTrue(og[0].startswith('http://testserver/media/'), og[0])
                self.assertNotIn('banner', og[0])
                # Post/Project store no dimensions — never claim the banner's 1200x630.
                self.assertEqual(self._meta(html, 'property', 'og:image:width'), [])

    def test_detail_page_without_image_keeps_the_site_banner(self):
        html = self.client.get(self.bare_post.get_absolute_url()).content.decode()
        self.assertEqual(self._meta(html, 'property', 'og:image'), ['http://testserver/media/og/banner.png'])
        self.assertEqual(self._meta(html, 'property', 'og:image:width'), ['1200'])

    def test_every_jsonld_block_parses(self):
        """The @graph is hand-assembled — one stray comma kills every rich
        result on the page silently."""
        import json

        pages = ['/xo/', '/en/about/', '/ru/blog/', '/uz/projects/', '/xo/team/', '/en/contact/',
                 self.post.get_absolute_url(), self.project.get_absolute_url()]
        for path in pages:
            with self.subTest(path=path):
                html = self.client.get(path).content.decode()
                blocks = html.split('<script type="application/ld+json">')[1:]
                self.assertTrue(blocks)
                for block in blocks:
                    json.loads(block.split('</script>')[0])

    def test_website_node_is_identical_in_every_locale(self):
        """Was the HTML-escaped <title> ("Qo&#x27;ziboyev … &amp;"), different
        per locale, with a SearchAction target that 302'd to the locale URL."""
        for lang in self.LANGS:
            with self.subTest(lang=lang):
                site = next(n for n in self._graph(f'/{lang}/') if n['@type'] == 'WebSite')
                self.assertEqual(site['name'], 'Jayson Khan')
                self.assertEqual(site['alternateName'], ['JaysonKhan', "Jahongir Qo'ziboyev"])
                target = site['potentialAction']['target']
                self.assertEqual(target, f'https://jaysonkhan.com/{lang}/blog/search/?q={{search_term_string}}')
                self.assertEqual(self.client.get(f'/{lang}/blog/search/', {'q': 'x'}).status_code, 200)

    def test_entity_graph_links_the_products_to_the_person(self):
        graph = self._graph('/en/')
        by_id = {n['@id']: n for n in graph if '@id' in n}
        person = by_id['https://jaysonkhan.com#person']
        self.assertEqual(person['name'], 'Jayson Khan')
        self.assertIn("Jahongir Qo'ziboyev", person['alternateName'])
        for url in ('https://github.com/JaysonKhan', 'https://www.linkedin.com/in/jaysonkhan/',
                    'https://t.me/jaysonkhan'):
            self.assertIn(url, person['sameAs'])
        for org_id, url in (('https://uzexam.uz/#organization', 'https://uzexam.uz'),
                            ('https://edustats.uz/#organization', 'https://edustats.uz')):
            with self.subTest(org=org_id):
                org = by_id[org_id]
                self.assertEqual(org['@type'], 'Organization')
                self.assertEqual(org['url'], url)
                self.assertEqual(org['founder'], {'@id': person['@id']})

    def test_telegram_sdk_loads_in_body_right_before_the_auto_login(self):
        """Moved out of <head> (sync = render-blocking). It must stay a sync
        script and be the one immediately preceding the inline auto-login,
        which reads window.Telegram the moment it runs."""
        html = self.client.get('/xo/').content.decode()
        tag = '<script src="https://telegram.org/js/telegram-web-app.js"></script>'
        self.assertEqual(html.count('telegram-web-app.js'), 1)
        sdk = html.index(tag)
        login = html.index('/* Telegram WebApp auto-login */')
        self.assertLess(html.index('<body'), sdk)
        self.assertLess(sdk, login)
        self.assertEqual(html[sdk + len(tag):login].count('<script'), 1)
