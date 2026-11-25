"""Public My Services pages (4 languages), the bare app link, the staff dashboard and admin lists."""
import re
import uuid

from core.models import SiteSettings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import translation

from .helpers import FEEDBACK_URL, ServicesTestCase, session_start, turn

LANGS = ('xo', 'uz', 'ru', 'en')


def stat(html: str, name: str) -> str:
    match = re.search(rf'data-stat="{name}">([^<]*)<', html)
    return match.group(1) if match else None


class PublicPagesTest(ServicesTestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def fill(self, installs=5):
        for _ in range(installs):
            records = [session_start(target='en'), turn(turn_id=1, e2e=1000), turn(turn_id=2, e2e=2000, minutes=8)]
            self.assertEqual(self.send(records, str(uuid.uuid4())).status_code, 202)

    def test_livebridge_page_shows_the_figures_in_every_language(self):
        self.fill()
        for lang in LANGS:
            with self.subTest(lang=lang), translation.override(lang):
                url = reverse('services_livebridge')
                self.assertEqual(url, f'/{lang}/services/livebridge/')
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertEqual(stat(html, 'installs'), '5')
                self.assertEqual(stat(html, 'active7'), '5')
                self.assertEqual(stat(html, 'turns'), '10')
                self.assertEqual(stat(html, 'p50'), '1500')
                self.assertEqual(stat(html, 'p95'), '2000')
                self.assertNotIn('data-svc-empty', html)
                self.assertIn('https://github.com/JaysonKhan/livebridge', html)

    def test_strings_are_translated(self):
        self.fill()
        with translation.override('ru'):
            html = self.client.get(reverse('services_livebridge')).content.decode()
        self.assertIn('LiveBridge в цифрах', html)
        self.assertIn('Узбекский → Английский', html)  # the language breakdown (5 installs)
        with translation.override('xo'):
            html = self.client.get(reverse('services')).content.decode()
        self.assertIn('Mening servislarim', html)

    def test_empty_state(self):
        with translation.override('en'):
            html = self.client.get(reverse('services_livebridge')).content.decode()
        self.assertIn('data-svc-empty', html)
        self.assertIn('No figures yet', html)
        self.assertIsNone(stat(html, 'installs'))

    def test_breakdown_below_five_installs_is_not_shown(self):
        self.fill(installs=4)
        with translation.override('en'):
            html = self.client.get(reverse('services_livebridge')).content.decode()
        self.assertEqual(stat(html, 'installs'), '4')
        self.assertNotIn('Uzbek → English', html)
        self.assertIn('Shown once at least 5 installs contribute.', html)

    def test_other_language_pairs_are_named_in_the_page_language(self):
        for _ in range(5):
            self.send([session_start(target='de', my='tr'), turn()], str(uuid.uuid4()))
        with translation.override('en'):
            html = self.client.get(reverse('services_livebridge')).content.decode()
        self.assertIn('Turkish → German', html)

    def test_index_renders_in_every_language_and_links_to_the_app(self):
        for lang in LANGS:
            with self.subTest(lang=lang), translation.override(lang):
                response = self.client.get(reverse('services'))
                self.assertEqual(response.status_code, 200)
                self.assertIn(f'href="/{lang}/services/livebridge/"', response.content.decode())

    def test_bare_app_link_reaches_the_page(self):
        response = self.client.get('/services/livebridge/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], '/xo/services/livebridge/')
        response = self.client.get('/services/livebridge/', follow=True, HTTP_ACCEPT_LANGUAGE='ru')
        self.assertEqual(response.redirect_chain[-1][0], '/ru/services/livebridge/')

    def test_menu_links_to_my_services_next_to_demo(self):
        with translation.override('en'):
            html = self.client.get(reverse('about')).content.decode()
        self.assertEqual(html.count('href="/en/services/"'), 2)  # desktop menu + mobile menu


class OwnerSideTest(ServicesTestCase):
    def setUp(self):
        super().setUp()
        self.dashboard = reverse('admin:apptelemetry_telemetryrecord_dashboard')

    def test_dashboard_is_refused_for_anonymous_users(self):
        response = self.client.get(self.dashboard)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_dashboard_and_lists_render_for_staff(self):
        install_id = str(uuid.uuid4())
        self.send([session_start(), turn()], install_id)
        self.post_json(FEEDBACK_URL, {'app': 'livebridge', 'message': 'Juda zo\'r ilova', 'rating': 5})
        staff = get_user_model().objects.create_user(
            username='owner', email='owner@example.com', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(staff)
        response = self.client.get(self.dashboard)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="lb-chart-day"', html)
        self.assertIn('id="lb-charts"', html)
        self.assertIn('Juda zo&#x27;r ilova', html)
        for name in ('appinstall', 'telemetryrecord', 'appfeedback'):
            with self.subTest(model=name):
                self.assertEqual(self.client.get(reverse(f'admin:apptelemetry_{name}_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:apptelemetry_appfeedback_change', args=[1])).status_code, 200)
