"""
RSS / Atom feeds for the blog.
"""
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed

from .models import Post


class LatestPostsFeed(Feed):
    """RSS 2.0 feed of the latest published blog posts."""
    title = "JaysonKhan Blog"
    link = "/blog/"
    description = "Latest posts on Flutter, mobile development, and software engineering."

    def items(self):
        return (
            Post.objects
            .filter(is_published=True)
            .select_related('category', 'author')
            .defer('content_rich', 'content_rich_xo', 'content_rich_uz', 'content_rich_ru', 'content_rich_en')
            .order_by('-created_at')[:15]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or ""

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        return item.created_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_categories(self, item):
        cats = []
        if item.category:
            cats.append(item.category.name)
        return cats


class LatestPostsAtomFeed(LatestPostsFeed):
    """Atom 1.0 version of the blog feed."""
    feed_type = Atom1Feed
    subtitle = LatestPostsFeed.description
