from django.test import TestCase
from portfolio.models import Skill, Project
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
