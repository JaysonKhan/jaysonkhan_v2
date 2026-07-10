from blog.models import Post
from blog.services import BlogRepository, BlogService
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class BlogServiceTest(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.author = user_model.objects.create_user(
            username='author1',
            email='author1@example.com',
            password='secret123',
        )

        self.published = Post.objects.create(
            title='Published Post',
            slug='published-post',
            author=self.author,
            excerpt='Published excerpt',
            content_rich='<p>Published</p>',
            is_published=True,
        )
        self.draft = Post.objects.create(
            title='Draft Post',
            slug='draft-post',
            author=self.author,
            excerpt='Draft excerpt',
            content_rich='<p>Draft</p>',
            is_published=False,
        )
        self.service = BlogService(BlogRepository())

    def test_get_all_published_posts_returns_only_published(self):
        slugs = set(self.service.get_all_published_posts().values_list('slug', flat=True))
        self.assertIn(self.published.slug, slugs)
        self.assertNotIn(self.draft.slug, slugs)

    def test_get_post_details_returns_none_for_missing_slug(self):
        self.assertIsNone(self.service.get_post_details('missing-slug'))


class BlogWebViewTest(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.author = user_model.objects.create_user(
            username='author2',
            email='author2@example.com',
            password='secret123',
        )
        self.published = Post.objects.create(
            title='Live Post',
            slug='live-post',
            author=self.author,
            excerpt='Live excerpt',
            content_rich='<p>Live</p>',
            is_published=True,
        )
        self.draft = Post.objects.create(
            title='Hidden Post',
            slug='hidden-post',
            author=self.author,
            excerpt='Hidden excerpt',
            content_rich='<p>Hidden</p>',
            is_published=False,
        )

    def test_blog_detail_returns_200_for_published_post(self):
        response = self.client.get(reverse('blog_detail', kwargs={'slug': self.published.slug}))
        self.assertEqual(response.status_code, 200)

    def test_blog_detail_returns_404_for_missing_slug(self):
        response = self.client.get(reverse('blog_detail', kwargs={'slug': 'missing-post'}))
        self.assertEqual(response.status_code, 404)

    def test_blog_detail_returns_404_for_unpublished_post(self):
        response = self.client.get(reverse('blog_detail', kwargs={'slug': self.draft.slug}))
        self.assertEqual(response.status_code, 404)


class PostApiPermissionsTest(TestCase):
    def setUp(self):
        user_model = get_user_model()
        author = user_model.objects.create_user(
            username='author3',
            email='author3@example.com',
            password='secret123',
        )
        Post.objects.create(
            title='Public API Post',
            slug='public-api-post',
            author=author,
            excerpt='Visible in API',
            content_rich='<p>Public</p>',
            is_published=True,
        )
        Post.objects.create(
            title='Draft API Post',
            slug='draft-api-post',
            author=author,
            excerpt='Should not be visible',
            content_rich='<p>Draft</p>',
            is_published=False,
        )

    def test_posts_list_is_public_and_filters_unpublished(self):
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn('results', payload)
        slugs = [item['slug'] for item in payload['results']]
        self.assertIn('public-api-post', slugs)
        self.assertNotIn('draft-api-post', slugs)
