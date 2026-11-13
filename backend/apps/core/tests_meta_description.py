"""Meta descriptions: no page of the sitemap may come out too short.

Bing Webmaster (2026-11) flagged jaysonkhan.com pages whose description was
too short. The prod sweep (2026-11-13) found six under 70 characters: a blog
post with a one-line teaser (57–63, all four locales) and the ru/en team page
(62/63).
"""
import html
import re
from io import StringIO
from types import SimpleNamespace
from urllib.parse import urlsplit

from blog.models import Post
from core.models import SiteSettings
from core.sitemaps import SITEMAPS
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import translation
from ops.management.commands import apply_edtech_founder_copy, apply_xiva_copy
from portfolio.models import Project, TeamMember
from presentation.web.seo import (
    META_DESC_MAX,
    META_DESC_MIN,
    meta_description,
    plain_text,
    translated,
)

LANGS = ('xo', 'uz', 'ru', 'en')
# What Bing calls too short, per the audit brief; pages built by
# seo.meta_description go further and reach META_DESC_MIN.
SWEEP_MIN = 70

SITE = ("Jayson Khan (Jahongir Qo'ziboyev) — AI, mobile and full-stack developer in Uzbekistan, "
        "founder of UzExam and EduStats. 25+ apps, 85k+ questions.")


class MetaDescriptionBuilderTest(SimpleTestCase):
    def test_long_enough_teaser_is_kept_as_written(self):
        teaser = 'x' * META_DESC_MIN
        self.assertEqual(meta_description(teaser, 'body', SITE), teaser)
        # Even past the limit: an author-written teaser is never cut here.
        self.assertEqual(meta_description('y' * 300, 'body'), 'y' * 300)

    def test_short_teaser_is_finished_with_the_next_parts(self):
        got = meta_description('JaysonKhan at GITA Academy. Cohort 5. January – September 2023.', '', SITE)
        self.assertEqual(
            got,
            "JaysonKhan at GITA Academy. Cohort 5. January – September 2023. Jayson Khan (Jahongir "
            "Qo'ziboyev) — AI, mobile and full-stack developer in Uzbekistan, founder…",
        )
        self.assertGreaterEqual(len(got), META_DESC_MIN)
        self.assertLessEqual(len(got), META_DESC_MAX)

    def test_extension_ends_on_a_whole_sentence_when_one_fits(self):
        got = meta_description(
            'JaysonKhan GITA akademiyasida. 5-guruh. 2023.01 — 2023-09',
            "GITA — Mobile dasturchilarni yetishtirib chiqarish bo‘yicha O‘zbekistondagi eng zo‘r "
            "o‘quv markaz!!! Hozir bu yerda man o'z tariximni aytib berishim mumkin edi.",
            SITE,
        )
        self.assertEqual(
            got,
            "JaysonKhan GITA akademiyasida. 5-guruh. 2023.01 — 2023-09. GITA — Mobile dasturchilarni "
            "yetishtirib chiqarish bo‘yicha O‘zbekistondagi eng zo‘r o‘quv markaz!!!",
        )

    def test_parts_are_added_only_until_it_is_long_enough(self):
        body = 'A second sentence that makes the description comfortably long enough for a search snippet.'
        got = meta_description('A short teaser.', body, SITE)
        self.assertEqual(got, f'A short teaser. {body}')
        self.assertNotIn('Jayson Khan', got)

    def test_teaser_cut_from_the_body_is_not_repeated(self):
        body = 'Alpha beta gamma delta. ' * 8
        got = meta_description('Alpha beta gamma …', body)
        self.assertTrue(got.startswith('Alpha beta gamma delta. Alpha beta gamma delta.'))
        self.assertLessEqual(len(got), META_DESC_MAX)

    def test_empty_parts_are_skipped(self):
        self.assertEqual(meta_description('', None, '  '), '')
        self.assertEqual(meta_description('', None, SITE), SITE)
        self.assertEqual(meta_description('Only this.'), 'Only this.')

    def test_whitespace_is_collapsed_to_one_line(self):
        self.assertEqual(meta_description('Two\nlines\t here.'), 'Two lines here.')

    def test_plain_text_keeps_blocks_apart(self):
        rich = '<h1><strong>GITA</strong> &mdash; markaz!!!</h1><hr><h3>Hozir&nbsp;bu yerda</h3><p>a<br>b</p>'
        self.assertEqual(plain_text(rich), 'GITA — markaz!!! Hozir bu yerda a b')
        self.assertEqual(plain_text(None), '')


class MetaDescriptionSweepTest(TestCase):
    """Render sweep over every sitemap URL in the four locales."""

    GITA_BODY = (
        '<h1><strong>GITA</strong> &mdash; Mobile dasturchilarni yetishtirib chiqarish bo&lsquo;yicha '
        'O&lsquo;zbekistondagi eng zo&lsquo;r o&lsquo;quv markaz!!!</h1><hr>'
        "<h3>Hozir bu yerda man o'z tariximni aytib berishim mumkin edi.</h3>"
    )

    @classmethod
    def setUpTestData(cls):
        # Bare `title=`/`excerpt=` kwargs land in the ACTIVE language's column,
        # and an earlier test may have left another language active.
        with translation.override('xo'):
            # The copy production serves. Written column by column: the seeder
            # commands keep an existing xo value, and prod's xo columns hold exactly
            # these strings (compared with the live pages on 2026-11-13).
            site = SiteSettings.load()
            for copy in (apply_xiva_copy.COPY, apply_edtech_founder_copy.COPY):
                for field, values in copy.items():
                    for lang, text in values.items():
                        if hasattr(site, f'{field}_{lang}'):
                            setattr(site, f'{field}_{lang}', text)
            site.apps_section_visible = True
            site.save()
            call_command('apply_edtech_projects', stdout=StringIO())

            author = get_user_model().objects.create_user(
                username='meta-author', email='meta@example.com', password='secret123')
            # Mirrors the flagged prod post: one-line teasers, body written in xo
            # only (ru/en hold the untranslated copy from the first backfill).
            cls.short_post = Post.objects.create(
                slug='gita', author=author, is_published=True,
                title_xo='Gita Dasturchilar Akademiyasi', title_uz='Gita Dasturchilar Akademiyasi',
                title_ru='Академия программистов Gita', title_en='Gita Developers Academy',
                excerpt_xo='JaysonKhan GITA akademiyasida. 5-guruh. 2023.01 — 2023-09',
                excerpt_uz='JaysonKhan GITA akademiyasida. 5-guruh. 2023.01 — 2023-09',
                excerpt_ru='JaysonKhan в академии GITA. Группа 5. Январь — сентябрь 2023.',
                excerpt_en='JaysonKhan at GITA Academy. Cohort 5. January – September 2023.',
                content_rich_xo=cls.GITA_BODY, content_rich_ru=cls.GITA_BODY, content_rich_en=cls.GITA_BODY,
            )
            cls.long_excerpt = (
                'jaysonkhan.com — my professional portfolio site is officially live. It features '
                'projects, a blog, technical skills, Telegram integration, and a lot more.'
            )
            cls.long_post = Post.objects.create(
                title='Launch', slug='launch', author=author, is_published=True,
                excerpt=cls.long_excerpt, content_rich='<p>Body.</p>')
            Post.objects.create(title='Bare', slug='bare', author=author, is_published=True)
            cls.bare_project = Project.objects.create(title='Bare', slug='bare', is_visible=True)
            cls.short_project = Project.objects.create(
                title='Tiny', slug='tiny', is_visible=True, short_description='Short desc',
                description_rich='<p>A booking app for jet-ski rentals with online payments.</p>')
            for order, (name, role) in enumerate((
                ('DINA', {'xo': 'SEO / Growth', 'uz': "SEO / O'sish mutaxassisi",
                          'ru': 'SEO / Специалист по росту', 'en': 'SEO / Growth Specialist'}),
                ('NOVA', {'xo': 'Backend / Django Developer', 'uz': 'Backend / Django Dasturchi',
                          'ru': 'Backend / Django Разработчик', 'en': 'Backend / Django Developer'}),
            )):
                TeamMember.objects.create(
                    name=name, bio='Bio.', order=order, **{f'role_{lang}': text for lang, text in role.items()})

    def setUp(self):
        cache.clear()  # SiteSettings is cached 5 min — read the rows above,
        self.addCleanup(cache.clear)  # and do not leak them into the next test class

    def _description(self, path):
        resp = self.client.get(path)
        self.assertEqual(resp.status_code, 200, path)
        found = re.findall(r'<meta name="description" content="([^"]*)">', resp.content.decode())
        self.assertEqual(len(found), 1, path)
        return html.unescape(found[0])

    def _sitemap_paths(self):
        site = SimpleNamespace(domain='testserver')
        for sitemap_cls in SITEMAPS.values():
            for entry in sitemap_cls().get_urls(site=site):
                yield urlsplit(entry['location']).path

    def test_no_sitemap_page_has_a_short_description(self):
        paths = list(self._sitemap_paths())
        # 6 static pages + the fixtures above, each in four locales.
        self.assertGreaterEqual(len(paths), (6 + 3 + 2) * len(LANGS))
        for lang in LANGS:
            self.assertIn(f'/{lang}/blog/gita/', paths)
            self.assertIn(f'/{lang}/team/', paths)
        for path in paths:
            with self.subTest(path=path):
                self.assertGreaterEqual(len(self._description(path)), SWEEP_MIN)

    def test_detail_and_team_pages_reach_the_comfortable_length(self):
        for lang in LANGS:
            for path in ('blog/gita/', 'blog/bare/', 'projects/tiny/', 'projects/bare/', 'team/'):
                with self.subTest(lang=lang, path=path):
                    text = self._description(f'/{lang}/{path}')
                    self.assertGreaterEqual(len(text), META_DESC_MIN)
                    self.assertLessEqual(len(text), META_DESC_MAX)

    def test_short_teaser_is_extended_with_the_xo_body_on_the_xo_page(self):
        self.assertEqual(
            self._description('/xo/blog/gita/'),
            "JaysonKhan GITA akademiyasida. 5-guruh. 2023.01 — 2023-09. GITA — Mobile dasturchilarni "
            "yetishtirib chiqarish bo‘yicha O‘zbekistondagi eng zo‘r o‘quv markaz!!!",
        )

    def test_untranslated_body_never_leaks_into_another_locale(self):
        """ru/en/uz show the xo body as a fallback; their description must
        stay in their own language — teaser + the localized site description."""
        for lang in ('uz', 'ru', 'en'):
            with self.subTest(lang=lang):
                with translation.override(lang):
                    teaser = self.short_post.excerpt
                    site = SiteSettings.load().meta_description
                text = self._description(f'/{lang}/blog/gita/')
                self.assertTrue(text.startswith(teaser), text)
                self.assertIn(site[:40], text)
                self.assertNotIn('dasturchilarni', text)

    def test_long_teaser_is_left_exactly_as_written(self):
        self.assertEqual(self._description('/en/blog/launch/'), self.long_excerpt)

    def test_short_project_one_liner_is_extended_with_its_description(self):
        with translation.override('xo'):
            site = SiteSettings.load().meta_description
        text = self._description('/xo/projects/tiny/')
        self.assertTrue(
            text.startswith(f'Short desc. A booking app for jet-ski rentals with online payments. {site[:40]}'),
            text)

    def test_seeded_project_descriptions_are_untouched(self):
        with translation.override('en'):
            teaser = Project.objects.get(slug='uzexam').short_description
        self.assertGreaterEqual(len(teaser), META_DESC_MIN)
        self.assertEqual(self._description('/en/projects/uzexam/'), teaser)

    def test_team_page_adds_the_roles_in_the_page_language(self):
        expected = {
            'ru': ('Небольшая студия — full-stack строители, дизайнеры, операторы. '
                   'SEO / Специалист по росту, Backend / Django Разработчик'),
            'en': ('A small studio of full-stack builders, designers and operators. '
                   'SEO / Growth Specialist, Backend / Django Developer'),
        }
        for lang, text in expected.items():
            with self.subTest(lang=lang):
                self.assertEqual(self._description(f'/{lang}/team/'), text)

    def test_xo_intro_keeps_its_wording(self):
        """The xo copy is the owner's voice — only ever appended to."""
        with translation.override('xo'):
            intro = SiteSettings.load().team_intro
        self.assertEqual(self._description('/xo/team/'), f'{intro} SEO / Growth, Backend / Django Developer')

    def test_translated_ignores_a_copy_of_the_xo_text(self):
        with translation.override('en'):
            self.assertEqual(translated(self.short_post, 'content_rich'), '')
            self.assertEqual(translated(self.short_post, 'excerpt'), self.short_post.excerpt_en)
        with translation.override('uz'):
            self.assertEqual(translated(self.short_post, 'content_rich'), '')
        with translation.override('xo'):
            self.assertEqual(translated(self.short_post, 'content_rich'), self.GITA_BODY)
