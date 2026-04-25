"""XML Sitemap classes for search engine crawlers (Google, Yandex, Bing).

Sections:
  - StaticViewSitemap  — home, projects, blog list, contact
  - ProjectSitemap     — visible portfolio projects
  - PostSitemap        — published blog posts

All sitemaps enforce `protocol = "https"` and `limit = 5000` (Google recommendation).
"""
from datetime import datetime, timezone

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from portfolio.models import Project
from blog.models import Post


def _to_aware(dt):
    """Normalize a datetime/date to tz-aware UTC. Returns None on invalid input.

    Django's sitemap framework calls `max()` on all lastmod values; mixing naive
    and aware datetimes raises TypeError. Always return a tz-aware value.
    """
    if dt is None:
        return None
    if hasattr(dt, "tzinfo"):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    # Convert date → datetime at UTC midnight
    try:
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    except (AttributeError, TypeError):
        return None


class StaticViewSitemap(Sitemap):
    """High-level static pages — home is priority 1.0, others weighted by importance."""

    protocol = "https"
    limit = 5000

    # (url_name, priority, changefreq)
    _PAGES = [
        ("home", 1.0, "daily"),
        ("projects", 0.9, "weekly"),
        ("team", 0.7, "monthly"),
        ("blog_list", 0.9, "daily"),
        ("contact", 0.6, "monthly"),
    ]

    def items(self):
        return self._PAGES

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]

    def lastmod(self, item):
        # Static pages are "current" — report today so crawlers re-check.
        return datetime.now(timezone.utc)


class ProjectSitemap(Sitemap):
    """Every visible portfolio project. Updated whenever a project is edited."""

    changefreq = "monthly"
    priority = 0.8
    protocol = "https"
    limit = 5000

    def items(self):
        return Project.objects.filter(is_visible=True).order_by("-created_at")

    def lastmod(self, obj):
        # Prefer updated_at if the model has it; fall back to created_at
        return _to_aware(getattr(obj, "updated_at", None) or obj.created_at)


class PostSitemap(Sitemap):
    """Every published blog post."""

    changefreq = "weekly"
    priority = 0.7
    protocol = "https"
    limit = 5000

    def items(self):
        return Post.objects.filter(is_published=True).order_by("-updated_at")

    def lastmod(self, obj):
        return _to_aware(obj.updated_at)
