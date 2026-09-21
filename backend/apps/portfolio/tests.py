from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override
from portfolio.models import Project, Skill
from portfolio.services import PortfolioRepository


class SkillModelTest(TestCase):
    def test_default_category_is_valid(self):
        skill = Skill(name='Flutter')
        skill.full_clean()
        skill.save()
        self.assertEqual(skill.category, 'mobile')


class PortfolioRepositoryTest(TestCase):
    def setUp(self):
        self.bot_project = Project.objects.create(
            title='Bot Project',
            slug='bot-project',
            is_bot=True,
            is_visible=True,
        )
        self.hidden_bot = Project.objects.create(
            title='Hidden Bot',
            slug='hidden-bot',
            is_bot=True,
            is_visible=False,
        )
        self.non_bot = Project.objects.create(
            title='Regular App',
            slug='regular-app',
            is_bot=False,
            is_visible=True,
        )

    def test_get_bot_projects_includes_flag_and_only_visible(self):
        slugs = set(PortfolioRepository.get_bot_projects().values_list('slug', flat=True))
        self.assertIn(self.bot_project.slug, slugs)
        self.assertNotIn(self.hidden_bot.slug, slugs)
        self.assertNotIn(self.non_bot.slug, slugs)


class ProjectApiPermissionsTest(TestCase):
    def setUp(self):
        Project.objects.create(
            title='Visible App',
            slug='visible-app',
            is_visible=True,
        )
        Project.objects.create(
            title='Hidden App',
            slug='hidden-app',
            is_visible=False,
        )

    def test_projects_list_is_public_and_filters_hidden(self):
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn('results', payload)
        slugs = [item['slug'] for item in payload['results']]
        self.assertIn('visible-app', slugs)
        self.assertNotIn('hidden-app', slugs)


class GalleryWallTest(TestCase):
    def setUp(self):
        from portfolio.models import GalleryImage
        for i in range(3):
            GalleryImage.objects.create(
                image=f'gallery/test-{i}.jpg', hint=f'Kadr {i}',
                width=600, height=400, order=i,
            )
        GalleryImage.objects.create(
            image='gallery/hidden.jpg', hint='Yashirin',
            width=600, height=400, is_visible=False,
        )

    def test_feed_returns_visible_images_with_aspect(self):
        from django.urls import reverse
        resp = self.client.get(reverse('gallery_feed'))
        data = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['total'], 3)
        self.assertFalse(data['has_next'])
        self.assertEqual(len(data['images']), 3)
        self.assertEqual(data['images'][0]['ar'], '1.5000')
        self.assertNotIn('Yashirin', [i['hint'] for i in data['images']])

    def test_home_renders_gallery_section(self):
        from django.urls import reverse
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'gallery-wall')
        self.assertContains(resp, 'data-feed-url')


class GalleryCoverTest(TestCase):
    """Cover (anime) bo'lsa devor cover'ni, lightbox esa asosiy rasmni beradi."""

    def test_feed_uses_cover_for_display_and_image_for_full(self):
        from django.urls import reverse
        from portfolio.models import GalleryImage
        GalleryImage.objects.create(
            image='gallery/real.jpg', cover='gallery/covers/anime.jpg',
            hint='Kadr', width=1000, height=500,
            cover_width=800, cover_height=800, order=0,
        )
        data = self.client.get(reverse('gallery_feed')).json()
        item = data['images'][0]
        # Devorda cover ko'rinadi (kvadrat), lightbox asosiy rasmni (2:1) ochadi
        self.assertIn('covers/anime.jpg', item['url'])
        self.assertEqual(item['ar'], '1.0000')
        self.assertIn('real.jpg', item['full'])
        self.assertEqual(item['full_ar'], '2.0000')

    def test_feed_falls_back_to_image_when_no_cover(self):
        from django.urls import reverse
        from portfolio.models import GalleryImage
        GalleryImage.objects.create(
            image='gallery/plain.jpg', hint='Oddiy',
            width=600, height=400, order=0,
        )
        item = self.client.get(reverse('gallery_feed')).json()['images'][0]
        self.assertIn('plain.jpg', item['url'])
        self.assertIn('plain.jpg', item['full'])
        self.assertEqual(item['ar'], '1.5000')


class GalleryDimensionRefreshTest(TestCase):
    """Fayl almashtirilganda o'lchamlar qayta o'qiladi (eski --ar layoutni buzmasin)."""

    @staticmethod
    def _png(w, h):
        from io import BytesIO

        from PIL import Image as PILImage
        buf = BytesIO()
        PILImage.new('RGB', (w, h)).save(buf, format='PNG')
        return buf.getvalue()

    def test_replacing_image_refreshes_dimensions(self):
        import tempfile

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from portfolio.models import GalleryImage
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                g = GalleryImage.objects.create(
                    image=SimpleUploadedFile('a.png', self._png(10, 20), 'image/png'),
                    hint='Kadr',
                )
                self.assertEqual((g.width, g.height), (10, 20))
                g.image = SimpleUploadedFile('b.png', self._png(30, 15), 'image/png')
                g.save()
                g.refresh_from_db()
                self.assertEqual((g.width, g.height), (30, 15))

    def test_clearing_cover_resets_cover_dimensions(self):
        from portfolio.models import GalleryImage
        g = GalleryImage.objects.create(
            image='gallery/x.jpg', hint='K', width=600, height=400,
            cover='gallery/covers/x.jpg', cover_width=800, cover_height=800,
        )
        g.cover = None
        g.save()
        g.refresh_from_db()
        self.assertEqual((g.cover_width, g.cover_height), (0, 0))
        # Fallback: devorda endi asosiy rasm aspekti ishlaydi
        self.assertEqual(g.display_aspect_css, '1.5000')

    def test_feed_survives_garbage_page_param(self):
        from django.urls import reverse
        from portfolio.models import GalleryImage
        GalleryImage.objects.create(
            image='gallery/x.jpg', hint='K', width=600, height=400,
        )
        for bad in ('abc', '-3', '', '9999'):
            resp = self.client.get(reverse('gallery_feed'), {'page': bad})
            self.assertEqual(resp.status_code, 200)


class TeamModalTest(TestCase):
    """Jamoa sahifasi: modal payload (json_script) + karta trigger atributlari."""

    def test_team_page_renders_payload_and_triggers(self):
        from django.urls import reverse
        from portfolio.models import TeamMember
        TeamMember.objects.create(
            name='Nova', role='Backend', bio='Bio matn', skills='Django, DRF',
            photo='team/nova.png', photo_real='team/real/nova.jpg',
            quote='Kod — she\'r', years_experience=3,
        )
        resp = self.client.get(reverse('team'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-team-id')
        self.assertContains(resp, 'id="team-data"')
        self.assertContains(resp, 'team/real/nova.jpg')
        self.assertContains(resp, 'team-modal.js')

    def test_payload_photo_real_empty_when_missing(self):
        import json

        from django.urls import reverse
        from portfolio.models import TeamMember
        TeamMember.objects.create(
            name='Aria', role='DevOps', bio='B', photo='team/aria.png',
        )
        resp = self.client.get(reverse('team'))
        html = resp.content.decode()
        start = html.index('id="team-data"')
        payload = html[html.index('>', start) + 1:html.index('</script>', start)]
        data = json.loads(payload)
        member = list(data.values())[0]
        self.assertEqual(member['photo_real'], '')
        self.assertEqual(member['photo'], '/media/team/aria.png')


class ProjectDiscoveryTest(TestCase):
    @staticmethod
    def projects_url(lang="en"):
        with override(lang):
            return reverse("projects")

    def setUp(self):
        from core.models import SiteSettings
        from django.core.cache import cache
        settings = SiteSettings.load()
        settings.apps_section_visible = True
        settings.save()
        cache.clear()
        self.mobile = Project.objects.create(title_en='Mobile practice', slug='mobile-practice',
            play_store_url='https://play.google.com/store/apps/details?id=example', order=1)
        self.web = Project.objects.create(title_en='Web practice', slug='web-practice',
            web_page_url='https://example.com/', order=2)
        self.bot = Project.objects.create(title_en='Bot practice', slug='bot-practice',
            web_page_url='https://t.me/example', is_bot=True, order=3)
        Project.objects.create(title='Hidden', slug='hidden-practice', is_visible=False)

    def test_filters_agree_between_page_and_api(self):
        expected = {'mobile': {self.mobile.slug}, 'web': {self.web.slug}, 'bot': {self.bot.slug}}
        for kind, slugs in expected.items():
            with self.subTest(kind=kind):
                page = self.client.get(self.projects_url(), {'filter': kind})
                api = self.client.get(reverse("project-list"), {'filter': kind}, HTTP_ACCEPT_LANGUAGE='en')
                self.assertEqual({p.slug for p in page.context['projects']}, slugs)
                self.assertEqual({p['slug'] for p in api.json()['results']}, slugs)
                self.assertContains(page, 'aria-current="page"')

    def test_search_matches_technology_and_preserves_query_in_tabs(self):
        tech = Skill.objects.create(name='Flutter')
        self.mobile.technologies.add(tech)
        response = self.client.get(self.projects_url(), {'q': 'Flutter'})
        self.assertEqual([p.slug for p in response.context['projects']], [self.mobile.slug])
        self.assertTrue(all('q=Flutter' in t['url'] for t in response.context['filter_tabs']))
        api = self.client.get(reverse("project-list"), {'q': 'Flutter'}, HTTP_ACCEPT_LANGUAGE='en')
        self.assertEqual([p['slug'] for p in api.json()['results']], [self.mobile.slug])

    def test_mobile_continuation_does_not_pull_in_web_projects(self):
        for i in range(12):
            Project.objects.create(title_en=f'Mobile {i}', slug=f'mobile-{i}',
                play_store_url='https://example.com/app', order=10+i)
        page = self.client.get(self.projects_url(), {'filter': 'mobile'})
        first = {p.slug for p in page.context['projects']}
        api = self.client.get(reverse("project-list"), {'filter': 'mobile', 'page': 2}, HTTP_ACCEPT_LANGUAGE='en')
        following = {p['slug'] for p in api.json()['results']}
        self.assertEqual(len(first), 10)
        self.assertEqual(len(following), 3)
        self.assertFalse(first & following)
        self.assertNotIn(self.web.slug, following)

    def test_metric_dates_and_labels_survive_api_continuation(self):
        self.web.stats = [{'v':'85k+', 'l':'Published questions', 'as_of':'2026-09-21'}]
        self.web.save()
        api = self.client.get(reverse("project-list"), {'filter': 'web'}, HTTP_ACCEPT_LANGUAGE='ru')
        item = api.json()['results'][0]
        self.assertEqual(item['stats_as_of'], '2026-09-21')
        self.assertEqual(item['stats'][0]['l'], 'Опубликованных вопросов')
        self.assertContains(self.client.get(self.projects_url("ru")), 'datetime="2026-09-21"')


class ProjectFactsRefreshTest(TestCase):
    def test_seeders_are_repeatable_and_keep_verified_definitions(self):
        import io
        from django.core.management import call_command
        from core.models import SiteSettings
        from django.utils.translation import override
        for _ in range(2):
            call_command('apply_edtech_projects', stdout=io.StringIO())
            call_command('apply_edtech_founder_copy', stdout=io.StringIO())
        self.assertEqual(Project.objects.filter(slug__in=['uzexam','edustats','vaygo']).count(), 3)
        edustats = Project.objects.get(slug='edustats')
        self.assertEqual([s['v'] for s in edustats.stats], ['53k+', '193', '121'])
        uzexam = Project.objects.get(slug='uzexam')
        self.assertEqual([s['v'] for s in uzexam.stats], ['85k+', '21k+', '7'])
        self.assertIn('Flutter', list(uzexam.technologies.values_list('name', flat=True)))
        self.assertNotIn('Flutter', list(edustats.technologies.values_list('name', flat=True)))
        settings = SiteSettings.load()
        self.assertEqual((settings.stat_3_count, settings.stat_4_count), (85, 21))
        for lang in ('xo','uz','ru','en'):
            with override(lang):
                self.assertNotIn('52k+', edustats.short_description)
                self.assertNotIn('60k+', uzexam.short_description)
                self.assertEqual(self.client.get(reverse("projects")).status_code, 200)
