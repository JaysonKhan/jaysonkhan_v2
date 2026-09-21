import json

from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse
from interactions.models import Comment, CommentReaction
from portfolio.models import Project
from telegram.models import TelegramEntity


class InteractionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = TelegramEntity.objects.create(
            telegram_id=12345,
            first_name="Test",
            username="testuser",
            auth_date=123456789
        )
        self.project = Project.objects.create(
            title="Test Project",
            slug="test-project",
            description_rich="Test Description",
            is_visible=True
        )
        self.ct = ContentType.objects.get_for_model(self.project)

    def test_add_comment_requires_telegram_session(self):
        url = reverse('interactions:add_comment', args=['portfolio', 'project', self.project.pk])
        response = self.client.post(url, {'text': 'Hello world'})
        self.assertEqual(response.status_code, 401)

    def test_add_comment(self):
        # Setup session
        session = self.client.session
        session['tg_profile_id'] = self.profile.pk
        session.save()

        url = reverse('interactions:add_comment', args=['portfolio', 'project', self.project.pk])
        response = self.client.post(url, {'text': 'Hello world'})
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.text, 'Hello world')
        self.assertTrue(comment.is_approved)
        self.assertFalse(comment.is_reviewed)

    def test_toggle_reaction(self):
        # Setup session
        session = self.client.session
        session['tg_profile_id'] = self.profile.pk
        session.save()

        comment = Comment.objects.create(
            author=self.profile,
            content_type=self.ct,
            object_id=self.project.pk,
            text="Comment to react to",
            is_approved=True
        )

        url = reverse('interactions:toggle_comment_reaction', args=[comment.id])
        
        # Add reaction
        response = self.client.post(url, json.dumps({'emoji': '👍'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CommentReaction.objects.count(), 1)
        
        # Remove reaction (toggle)
        response = self.client.post(url, json.dumps({'emoji': '👍'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CommentReaction.objects.count(), 0)


class DisplayNameSanitizationTest(TestCase):
    """clean_public_name: tofu/format chars stripped, junk names fall back."""

    def test_tofu_combining_run_falls_back_to_username(self):
        from telegram.models import TelegramEntity
        e = TelegramEntity.objects.create(
            telegram_id=111, auth_date=1,
            first_name="••• -" + "ࠣ" * 20 + " ----",
            username="polat",
        )
        self.assertEqual(e.safe_display_name, "@polat")
        self.assertEqual(e.safe_initial, "P")

    def test_punctuation_only_name_without_username_uses_fallback(self):
        from telegram.models import TelegramEntity
        e = TelegramEntity.objects.create(telegram_id=2224821, auth_date=1, first_name=".")
        self.assertEqual(e.safe_display_name, "User #4821")

    def test_fancy_math_letters_fold_to_ascii(self):
        from telegram.models import clean_public_name
        self.assertEqual(clean_public_name("\U0001d475\U0001d468\U0001d474\U0001d46c"), "NAME")

    def test_normal_names_kept_and_capped(self):
        from telegram.models import clean_public_name
        self.assertEqual(clean_public_name("Polat Alemdar"), "Polat Alemdar")
        self.assertEqual(len(clean_public_name("A" * 80)), 40)


class CommentApiHardeningTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = TelegramEntity.objects.create(
            telegram_id=777, auth_date=1, first_name="<img src=x onerror=alert(1)>", username="xssuser",
        )
        self.project = Project.objects.create(
            title="P", slug="p1", description_rich="d", is_visible=True,
        )
        self.ct = ContentType.objects.get_for_model(self.project)

    def _login(self):
        s = self.client.session
        s['tg_profile_id'] = self.profile.pk
        s.save()

    def test_list_serializes_safe_name_and_unescaped_text(self):
        Comment.objects.create(
            author=self.profile, content_type=self.ct, object_id=self.project.pk,
            text="1 &lt; 2 &amp; 3", is_approved=True,
        )
        resp = self.client.get(
            reverse('interactions:list_comments'),
            {'app_label': 'portfolio', 'model': 'project', 'object_id': self.project.pk},
        )
        data = resp.json()['comments'][0]
        # Name cleaned server-side; the client renders it via textContent
        self.assertNotIn('ࠣ', data['author']['display_name'])
        self.assertEqual(data['text'], '1 < 2 & 3')

    def test_reaction_emoji_allowlist(self):
        comment = Comment.objects.create(
            author=self.profile, content_type=self.ct, object_id=self.project.pk,
            text="hi", is_approved=True,
        )
        self._login()
        url = reverse('interactions:toggle_comment_reaction', args=[comment.pk])
        bad = self.client.post(url, json.dumps({'emoji': '<script>'}), content_type='application/json')
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(url, json.dumps({'emoji': '🔥'}), content_type='application/json')
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()['reactions'], {'🔥': 1})

    def test_error_message_follows_url_language_prefix(self):
        # interactions URLs live inside i18n_patterns — the /uz/ prefix decides
        # the response language (matches the page the visitor is on).
        from django.utils.translation import override
        with override('uz'):
            url = reverse('interactions:add_comment', args=['portfolio', 'project', self.project.pk])
        self.assertTrue(url.startswith('/uz/'))
        resp = self.client.post(url, {'text': 'salom'})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['error'], 'Avval Telegram orqali kiring')


class DiscussionContractTest(TestCase):
    def setUp(self):
        self.profile = TelegramEntity.objects.create(telegram_id=987654, first_name='Reader', auth_date=1)
        self.project = Project.objects.create(title='Discussion', slug='discussion', is_visible=True)
        self.ct = ContentType.objects.get_for_model(self.project)
        self.root = Comment.objects.create(author=self.profile, content_type=self.ct, object_id=self.project.pk, text='A root comment')
        session = self.client.session
        session['tg_profile_id'] = self.profile.pk
        session.save()
        self.params = {'app_label': 'portfolio', 'model': 'project', 'object_id': self.project.pk}

    def reply(self, text='A reply'):
        return Comment.objects.create(author=self.profile, content_type=self.ct, object_id=self.project.pk, parent=self.root, text=text)

    def test_replies_have_reachable_pagination_and_deep_link_page(self):
        replies = [self.reply(f'Reply {i}') for i in range(13)]
        url = reverse('interactions:list_replies', args=[self.root.pk])
        first = self.client.get(url).json()
        second = self.client.get(url, {'page': 2}).json()
        self.assertEqual((len(first['replies']), len(second['replies'])), (10, 3))
        self.assertTrue(first['has_next'])
        self.assertFalse(second['has_next'])
        focused = self.client.get(url, {'focus': replies[-1].pk}).json()
        self.assertEqual(focused['page'], 2)
        self.assertIn(replies[-1].pk, [r['id'] for r in focused['replies']])

    def test_hidden_parent_blocks_reply_listing_post_and_reaction(self):
        reply = self.reply()
        self.root.is_approved = False
        self.root.save()
        self.assertEqual(self.client.get(reverse('interactions:list_replies', args=[self.root.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('interactions:toggle_comment_reaction', args=[reply.pk]), {'emoji': '👍'}).status_code, 404)
        self.assertEqual(self.client.post(reverse('interactions:add_comment', args=['portfolio', 'project', self.project.pk]), {'text': 'Hidden parent reply', 'parent_id': self.root.pk}).status_code, 400)
        self.assertEqual(self.client.get(reverse('interactions:list_comments'), self.params).json()['discussion_count'], 0)

    def test_hidden_target_blocks_all_discussion_endpoints(self):
        self.project.is_visible = False
        self.project.save()
        endpoints = [('get', reverse('interactions:list_comments'), self.params),
                     ('get', reverse('interactions:list_replies', args=[self.root.pk]), {}),
                     ('post', reverse('interactions:add_comment', args=['portfolio', 'project', self.project.pk]), {'text': 'Hidden target'}),
                     ('post', reverse('interactions:toggle_like', args=['portfolio', 'project', self.project.pk]), {}),
                     ('post', reverse('interactions:toggle_comment_reaction', args=[self.root.pk]), {'emoji': '👍'})]
        for method, url, data in endpoints:
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url, data).status_code, 404)

    def test_malformed_target_and_reaction_do_not_crash(self):
        self.assertEqual(self.client.get(reverse('interactions:list_comments'), dict(self.params, object_id='oops')).status_code, 404)
        url = reverse('interactions:toggle_comment_reaction', args=[self.root.pk])
        for data in ['null', '[]', '{"emoji": 7}', '{']:
            self.assertEqual(self.client.post(url, data, content_type='application/json').status_code, 400)

    def test_serializer_uses_prefetched_counts_without_extra_queries(self):
        from interactions.services import comment_queryset, serialize_comment
        for _ in range(4):
            self.reply()
        rows = list(comment_queryset(self.ct, self.project.pk))
        with self.assertNumQueries(0):
            result = [serialize_comment(c, self.profile.pk) for c in rows]
        self.assertEqual(next(c for c in result if c['id'] == self.root.pk)['reply_count'], 4)

    def test_new_post_returns_own_comment_without_reloading_threads(self):
        from django.test import override_settings
        with override_settings(COMMENT_NEW_USER_RATE_COUNT=20):
            response = self.client.post(reverse('interactions:add_comment', args=['portfolio', 'project', self.project.pk]), {'text': 'A fresh contribution'})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['comment']['is_own'])
        self.assertEqual(response.json()['comment']['text'], 'A fresh contribution')

    def test_pending_post_is_not_returned_as_public_comment(self):
        from django.test import override_settings
        with override_settings(COMMENT_NEW_USER_RATE_COUNT=20):
            response = self.client.post(reverse('interactions:add_comment', args=['portfolio', 'project', self.project.pk]), {'text': 'See https://example.com'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['status'], 'pending')
        self.assertIsNone(response.json()['comment'])

    def test_total_includes_visible_replies_and_focus_locates_thread(self):
        reply = self.reply()
        data = self.client.get(reverse('interactions:list_comments'), dict(self.params, focus=reply.pk)).json()
        self.assertEqual((data['total_count'], data['discussion_count']), (1, 2))
        self.assertEqual(data['focus_thread']['id'], self.root.pk)

    def test_banned_reader_cannot_react_or_like(self):
        from interactions.models import UserBan
        UserBan.objects.create(profile=self.profile, ban_type='ban')
        self.assertEqual(self.client.post(reverse('interactions:toggle_like', args=['portfolio', 'project', self.project.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('interactions:toggle_comment_reaction', args=[self.root.pk]), {'emoji': '👍'}).status_code, 403)
