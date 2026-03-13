"""
XML Sitemap classes for django.contrib.sitemaps.

Sections:
  - StaticViewSitemap  — home, projects, blog list, contact
  - ProjectSitemap     — visible projects
  - PostSitemap        — published blog posts
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from portfolio.models import Project
from blog.models import Post


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'projects', 'blog_list', 'contact']

    def location(self, item):
        return reverse(item)


class ProjectSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return Project.objects.filter(is_visible=True)

    def lastmod(self, obj):
        return obj.created_at


class PostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Post.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at
