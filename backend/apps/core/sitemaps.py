"""SEO-optimized sitemaps for Google / Bing / Yandex.

Layout (sitemap-index pattern + image extension inline):
    /sitemap.xml                ← sitemap-index entry point
    /sitemap-static.xml         ← landing + list pages (priority 1.0–0.9)
    /sitemap-projects.xml       ← portfolio projects with cover images
    /sitemap-blog.xml           ← published blog posts with featured images
    /sitemap-team.xml           ← team members section anchors

Why this design:
  • Sitemap-index lets Search Console show coverage per section — debug
    "12/27 projects indexed" issues per-segment.
  • Image extension inline (`<image:image>` per URL) — project covers and
    blog featured images surface in Google Images for the personal brand
    keywords ("JaysonKhan", "Qo'ziboyev Jahongir", "vibecoder").
  • Hreflang alternates per URL — 4 language variants (xo, uz, ru, en)
    point to each other so Google clusters them as one entity per page.
  • Per-section caching — projects/posts only regenerated hourly.

Cache: 1 hour. Crawlers hit /sitemap.xml hourly; data churns daily.
"""
from datetime import datetime, timezone

from blog.models import Post
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from portfolio.models import Project

# ── Constants ─────────────────────────────────────────────────────────────

LANGUAGES = ("xo", "uz", "ru", "en")
DEFAULT_LANG = "xo"
SITE_BASE = "https://jaysonkhan.com"


def _to_aware(dt):
    """Normalize a datetime/date to tz-aware UTC. Returns None on invalid input."""
    if dt is None:
        return None
    if hasattr(dt, "tzinfo"):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    try:
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    except (AttributeError, TypeError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _abs(path: str) -> str:
    """Convert relative path to absolute URL."""
    if path.startswith("http"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return SITE_BASE + path


def _strip_lang_prefix(path: str) -> str:
    """Remove leading /xo/ /uz/ /ru/ /en/ prefix so we can rebuild per-lang URLs."""
    for code in LANGUAGES:
        prefix = f"/{code}/"
        if path.startswith(prefix):
            return path[len(prefix) - 1:]  # keep leading slash
        if path == f"/{code}":
            return "/"
    return path


def _build_alternates(canonical_path: str) -> list:
    """Build hreflang alternates list pointing to each lang variant + x-default.

    `canonical_path` is the path *without* lang prefix (e.g. "/projects/foo/").
    Returns list of {lang_code, location} for all 4 langs + x-default → /xo/.
    """
    if not canonical_path.startswith("/"):
        canonical_path = "/" + canonical_path
    alternates = [
        {"lang_code": code, "location": f"{SITE_BASE}/{code}{canonical_path}"}
        for code in LANGUAGES
    ]
    alternates.append({
        "lang_code": "x-default",
        "location": f"{SITE_BASE}/{DEFAULT_LANG}{canonical_path}",
    })
    return alternates


# ── Image-extension mixin ─────────────────────────────────────────────────

class ImageSitemapMixin:
    """Adds `<image:image>` extension data per URL.

    Subclasses define `image_url(item)` and `image_caption(item)`.
    `templates/sitemap.xml` renders the inline image block.
    """

    def image_url(self, obj):  # override
        return None

    def image_caption(self, obj):  # override
        return ""

    def get_urls(self, page=1, site=None, protocol=None):
        urls = super().get_urls(page=page, site=site, protocol=protocol)
        for url_info in urls:
            item = url_info["item"]
            img = self.image_url(item)
            if img:
                url_info["image_url"] = _abs(img)
                url_info["image_caption"] = self.image_caption(item) or ""
        return urls


# ── Static pages ──────────────────────────────────────────────────────────

class StaticSitemap(Sitemap):
    """Top-level pages — home is priority 1.0, others weighted by importance.

    Lists only the canonical /xo/ URL per page; hreflang alternates point to
    /uz/, /ru/, /en/ siblings + x-default.
    """

    protocol = "https"

    # NOTE: don't name this `_items` — collides with Sitemap._items().
    PAGES = [
        ("home", 1.0, "daily"),
        # Person-entity page — the target for name queries, so it ranks just
        # under the homepage even though its content changes rarely.
        ("about", 0.9, "monthly"),
        ("projects", 0.9, "weekly"),
        ("team", 0.7, "monthly"),
        ("blog_list", 0.9, "daily"),
        ("contact", 0.6, "monthly"),
    ]

    def items(self):
        return self.PAGES

    def location(self, item):
        # `reverse()` with i18n_patterns returns /<lang>/path/ for current locale.
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]

    def lastmod(self, item):
        return _now()


# ── Projects ──────────────────────────────────────────────────────────────

class ProjectSitemap(ImageSitemapMixin, Sitemap):
    """Every visible portfolio project + cover image inline."""

    protocol = "https"
    changefreq = "monthly"
    priority = 0.8
    limit = 5000

    def items(self):
        return Project.objects.filter(is_visible=True).order_by("-order", "-created_at")

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return _to_aware(getattr(obj, "updated_at", None) or obj.created_at)

    def priority(self, obj):
        # Featured projects get higher crawl priority
        return 0.9 if getattr(obj, "is_featured", False) else 0.8

    def image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def image_caption(self, obj):
        title = (obj.title or "").strip()
        short = (obj.short_description or "").strip()
        return f"{title} — {short}".strip(" —") or title or "JaysonKhan project"


# ── Blog ──────────────────────────────────────────────────────────────────

class PostSitemap(ImageSitemapMixin, Sitemap):
    """Every published blog post + featured image inline."""

    protocol = "https"
    changefreq = "weekly"
    priority = 0.7
    limit = 5000

    def items(self):
        return Post.objects.filter(is_published=True).order_by("-updated_at")

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return _to_aware(obj.updated_at)

    def image_url(self, obj):
        if obj.featured_image:
            return obj.featured_image.url
        return None

    def image_caption(self, obj):
        title = (obj.title or "").strip()
        excerpt = (obj.excerpt or "").strip()[:120]
        return f"{title} — {excerpt}".strip(" —") or title or "JaysonKhan article"


# ── hreflang alternates decorator ─────────────────────────────────────────

def _attach_alternates(sitemap_cls):
    """Decorator: monkey-patch get_urls to inject alternates per URL.

    Each canonical URL (already lang-prefixed by reverse()/get_absolute_url())
    gets 4 hreflang sibling entries + x-default.
    """
    orig = sitemap_cls.get_urls

    def get_urls(self, page=1, site=None, protocol=None):
        urls = orig(self, page=page, site=site, protocol=protocol)
        for u in urls:
            if u.get("alternates"):
                continue
            # u["location"] is the absolute URL; extract path and strip lang prefix
            loc = u["location"]
            path = loc[len(SITE_BASE):] if loc.startswith(SITE_BASE) else loc
            canonical = _strip_lang_prefix(path)
            u["alternates"] = _build_alternates(canonical)
        return urls

    sitemap_cls.get_urls = get_urls
    return sitemap_cls


for _cls in (StaticSitemap, ProjectSitemap, PostSitemap):
    _attach_alternates(_cls)


# ── Public registry ───────────────────────────────────────────────────────

SITEMAPS = {
    "static": StaticSitemap,
    "projects": ProjectSitemap,
    "blog": PostSitemap,
}
