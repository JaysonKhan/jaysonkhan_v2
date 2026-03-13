from django.db import models
from django.utils.html import strip_tags

from .models import Post, Category, Tag


class BlogRepository:
    _PUBLISHED_BASE = (
        Post.objects
        .filter(is_published=True)
        .select_related('category', 'author')
        .prefetch_related('tags')
    )

    @staticmethod
    def get_published_posts():
        return (
            Post.objects
            .filter(is_published=True)
            .select_related('category', 'author')
            .prefetch_related('tags')
            .defer('content_rich')
        )

    @staticmethod
    def get_post_by_slug(slug):
        try:
            return (
                Post.objects
                .select_related('category', 'author')
                .prefetch_related('tags')
                .get(slug=slug, is_published=True)
            )
        except Post.DoesNotExist:
            return None

    @staticmethod
    def search_posts(query: str):
        """
        Search published posts by title, excerpt and tags.
        Uses PostgreSQL full-text search when available, falls back to icontains.
        """
        qs = (
            Post.objects
            .filter(is_published=True)
            .select_related('category', 'author')
            .prefetch_related('tags')
            .defer('content_rich')
        )
        try:
            from django.contrib.postgres.search import (
                SearchVector, SearchQuery, SearchRank,
            )
            vector = SearchVector('title', weight='A') + SearchVector('excerpt', weight='B')
            sq = SearchQuery(query)
            qs = (
                qs.annotate(rank=SearchRank(vector, sq))
                .filter(rank__gte=0.01)
                .order_by('-rank')
            )
        except Exception:
            # Fallback for SQLite (dev) — simple icontains
            qs = qs.filter(
                models.Q(title__icontains=query)
                | models.Q(excerpt__icontains=query)
                | models.Q(tags__name__icontains=query)
            ).distinct()
        return qs

    @staticmethod
    def get_related_posts(post, limit=3):
        """Return posts sharing tags with the given post."""
        tag_ids = post.tags.values_list('id', flat=True)
        if not tag_ids:
            return Post.objects.none()
        return (
            Post.objects
            .filter(is_published=True, tags__in=tag_ids)
            .exclude(pk=post.pk)
            .select_related('category', 'author')
            .prefetch_related('tags')
            .defer('content_rich')
            .annotate(shared_tags=models.Count('tags'))
            .order_by('-shared_tags', '-created_at')
            .distinct()[:limit]
        )

    @staticmethod
    def get_categories():
        return Category.objects.all()


class BlogService:
    def __init__(self, repository: BlogRepository):
        self.repository = repository

    def get_all_published_posts(self):
        return self.repository.get_published_posts()

    def get_post_details(self, slug):
        return self.repository.get_post_by_slug(slug)

    def search_posts(self, query: str):
        return self.repository.search_posts(query)

    def get_related_posts(self, post, limit=3):
        return self.repository.get_related_posts(post, limit)
