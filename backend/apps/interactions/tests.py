import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from portfolio.models import Project
from interactions.models import TelegramProfile, Comment, CommentReaction

class InteractionsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = TelegramProfile.objects.create(
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
