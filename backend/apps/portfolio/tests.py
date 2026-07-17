from django.test import TestCase
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
