"""IndexNow: key file, change detection, first-run cap, cron wiring."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from blog.models import Post
from core.models import SiteSettings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import translation
from ops.management.commands.indexnow import ENDPOINT, page_states
from ops.models import CronRun, CronStatus, IndexNowUrl, ManagedCron
from portfolio.models import Project

BASE = 'https://jaysonkhan.com'
LANGS = ('xo', 'uz', 'ru', 'en')


class IndexNowKeyFileTest(TestCase):
    def test_key_file_is_served_as_plain_text(self):
        resp = self.client.get(f'/{settings.INDEXNOW_KEY}.txt')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/plain')
        self.assertEqual(resp.content.decode(), settings.INDEXNOW_KEY)
        self.assertEqual(reverse('indexnow_key'), f'/{settings.INDEXNOW_KEY}.txt')

    def test_key_is_a_valid_indexnow_key(self):
        """Protocol: 8–128 characters out of a-z, A-Z, 0-9 and '-'."""
        self.assertRegex(settings.INDEXNOW_KEY, r'^[A-Za-z0-9-]{8,128}$')

    def test_any_other_txt_is_not_the_key(self):
        self.assertEqual(self.client.get('/0123456789abcdef0123456789abcdef.txt').status_code, 404)


class IndexNowCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with translation.override('xo'):  # bare kwargs land in the active language's column
            site = SiteSettings.load()
            site.apps_section_visible = True
            site.save()
            author = get_user_model().objects.create_user(
                username='indexnow-author', email='indexnow@example.com', password='secret123')
            cls.project = Project.objects.create(title='Probe', slug='probe', is_visible=True)
            cls.post = Post.objects.create(title='Note', slug='note', author=author, is_published=True)

    def setUp(self):
        cache.clear()
        patcher = mock.patch('ops.management.commands.indexnow.httpx.post')
        self.post_mock = patcher.start()
        self.addCleanup(patcher.stop)
        self._answer(200)

    def _answer(self, status, text=''):
        self.post_mock.return_value = mock.Mock(
            status_code=status, is_success=200 <= status < 300, text=text)

    def _run(self, *args):
        out = StringIO()
        call_command('indexnow', *args, stdout=out)
        return out.getvalue()

    def _sent(self):
        """urlList of the single POST the last run made."""
        self.post_mock.assert_called_once()
        return self.post_mock.call_args.kwargs['json']['urlList']

    def test_first_run_submits_every_sitemap_url_in_four_locales(self):
        self._run()
        sent = self._sent()
        for lang in LANGS:
            for path in ('', 'about/', 'projects/', 'team/', 'blog/', 'contact/',
                         'projects/probe/', 'blog/note/'):
                with self.subTest(lang=lang, path=path):
                    self.assertIn(f'{BASE}/{lang}/{path}', sent)
        self.assertEqual(sorted(sent), sorted(page_states()))
        self.assertEqual(IndexNowUrl.objects.count(), len(sent))

    def test_payload_names_the_host_and_the_key_file(self):
        self._run()
        self.assertEqual(self.post_mock.call_args.args, (ENDPOINT,))
        payload = self.post_mock.call_args.kwargs['json']
        self.assertEqual(payload['host'], 'jaysonkhan.com')
        self.assertEqual(payload['key'], settings.INDEXNOW_KEY)
        self.assertEqual(payload['keyLocation'], f'{BASE}/{settings.INDEXNOW_KEY}.txt')

    def test_first_run_is_capped_and_the_rest_drains_later(self):
        total = len(page_states())
        self._run('--limit', '5')
        first = self._sent()
        self.assertEqual(len(first), 5)
        # Most important first: the sitemap order starts with the homepage.
        self.assertEqual(first[:4], [f'{BASE}/{lang}/' for lang in LANGS])
        self.assertEqual(IndexNowUrl.objects.count(), 5)

        self.post_mock.reset_mock()
        self._run()
        rest = self._sent()
        self.assertEqual(len(rest), total - 5)
        self.assertFalse(set(first) & set(rest))

    def test_nothing_changed_sends_nothing(self):
        self._run()
        self.post_mock.reset_mock()
        out = self._run()
        self.post_mock.assert_not_called()
        self.assertIn('Nothing changed', out)

    def test_only_the_pages_showing_an_edited_row_are_resubmitted(self):
        self._run()
        self.post_mock.reset_mock()
        self.project.short_description_ru = 'Новое описание'
        self.project.save()
        self._run()
        # The Russian detail page plus the Russian pages that list projects.
        self.assertEqual(sorted(self._sent()), sorted([
            f'{BASE}/ru/', f'{BASE}/ru/projects/', f'{BASE}/ru/projects/probe/',
        ]))

    def test_site_copy_edit_resubmits_every_page_of_that_locale(self):
        """SiteSettings feeds the header, footer and page copy of every page."""
        self._run()
        self.post_mock.reset_mock()
        site = SiteSettings.load()
        site.site_tagline_en = 'A new English tagline.'
        site.save()
        self._run()
        sent = self._sent()
        self.assertEqual(sorted(sent), sorted(url for url in page_states() if url.startswith(f'{BASE}/en/')))

    def test_resaving_without_a_content_change_sends_nothing(self):
        """deploy.sh re-saves SiteSettings/projects on every deploy, the
        WakaTime cron rewrites its stats daily, the owner flips bot settings
        from Telegram. None of it changes a page."""
        self._run()
        self.post_mock.reset_mock()
        site = SiteSettings.load()
        site.wakatime_stats = {'total': '31h'}
        site.admin_notify_likes = not site.admin_notify_likes
        site.save()
        self.project.save()
        self.post.save()  # bumps updated_at only
        self._run()
        self.post_mock.assert_not_called()

    def test_unpublished_page_is_reported_once_and_forgotten(self):
        self._run()
        self.post_mock.reset_mock()
        Post.objects.filter(pk=self.post.pk).update(is_published=False)
        self._run()
        sent = self._sent()
        for lang in LANGS:
            with self.subTest(lang=lang):
                self.assertIn(f'{BASE}/{lang}/blog/note/', sent)   # gone → engines drop it
                self.assertIn(f'{BASE}/{lang}/blog/', sent)        # the list changed
                self.assertNotIn(f'{BASE}/{lang}/contact/', sent)
        self.assertFalse(IndexNowUrl.objects.filter(url__contains='/blog/note/').exists())

        self.post_mock.reset_mock()
        self._run()
        self.post_mock.assert_not_called()

    def test_rejected_submission_fails_loudly_and_is_retried(self):
        self._answer(403, 'SiteVerificationNotCompleted')
        with self.assertRaisesMessage(CommandError, 'IndexNow HTTP 403: SiteVerificationNotCompleted'):
            self._run()
        self.assertEqual(IndexNowUrl.objects.count(), 0)

        self.post_mock.reset_mock()
        self._answer(202)
        self._run()
        self.assertEqual(sorted(self._sent()), sorted(page_states()))

    def test_dry_run_sends_and_records_nothing(self):
        out = self._run('--dry-run')
        self.post_mock.assert_not_called()
        self.assertEqual(IndexNowUrl.objects.count(), 0)
        self.assertIn(f'{BASE}/en/projects/probe/', out)

    def test_all_resubmits_unchanged_urls(self):
        self._run()
        self.post_mock.reset_mock()
        self._run('--all')
        self.assertEqual(sorted(self._sent()), sorted(page_states()))


class IndexNowCronTest(TestCase):
    """The daily run goes through the managed crontab block (`cron_run`)."""

    def test_installer_block_schedules_the_wrapped_command(self):
        installer = Path(settings.BASE_DIR).parent / 'security' / 'install-servermonitor-cron.sh'
        block = installer.read_text().split('NEW_BLOCK=$(cat <<EOF')[1].split('\nEOF\n')[0]
        lines = [line for line in block.splitlines() if 'indexnow' in line and not line.startswith('#')]
        self.assertEqual(len(lines), 1)
        self.assertRegex(lines[0], r'^47 5 \* \* \*\s+cd \$PROJECT_DIR/backend && .*\$MANAGE cron_run indexnow >> \$LOG 2>&1$')

    def test_cron_is_in_the_admin_inventory(self):
        cron = ManagedCron.objects.get(command='indexnow')
        self.assertEqual(cron.schedule, '47 5 * * *')
        self.assertTrue(cron.enabled)

    def _cron_run(self, status, text=''):
        answer = mock.Mock(status_code=status, is_success=200 <= status < 300, text=text)
        with mock.patch('ops.management.commands.indexnow.httpx.post', return_value=answer), \
                redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            call_command('cron_run', 'indexnow')
        return CronRun.objects.get(command='indexnow')

    def test_wrapper_records_a_successful_run(self):
        run = self._cron_run(200)
        self.assertEqual(run.status, CronStatus.SUCCESS)
        self.assertIn('Submitted', run.stdout)

    def test_wrapper_records_a_rejection_as_failed(self):
        """A FAILED CronRun is what `cron_health_check` pages the owner about."""
        with self.assertRaises(SystemExit):
            self._cron_run(403, 'SiteVerificationNotCompleted')
        run = CronRun.objects.get(command='indexnow')
        self.assertEqual(run.status, CronStatus.FAILED)
        self.assertIn('IndexNow HTTP 403: SiteVerificationNotCompleted', run.error_summary)
