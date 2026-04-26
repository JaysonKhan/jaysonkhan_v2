from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
import environ
from presentation.web.views import custom_404_view, custom_500_view
from core.views import upload_media_view, robots_txt, health_check
from core.emoji_views import emoji_manager
from core.sitemaps import StaticViewSitemap, ProjectSitemap, PostSitemap
from blog.feeds import LatestPostsFeed, LatestPostsAtomFeed
from interactions.notifications.webhook import TelegramWebhookView

env = environ.Env()

# ── Admin URL: read from env, fall back to a non-obvious slug ─────────────────
ADMIN_URL = env('ADMIN_URL', default='admin/')

sitemaps = {
    'static': StaticViewSitemap,
    'projects': ProjectSitemap,
    'posts': PostSitemap,
}

# Non-localized URLs (admin, API, sitemap, webhooks)
urlpatterns = [
    path(ADMIN_URL + 'telegram/settings/', emoji_manager, name='telegram_settings'),
    path(ADMIN_URL + 'bot/', include('botproxy.urls')),
    path(ADMIN_URL + 'osint/', include('osint.urls')),
    path(ADMIN_URL, admin.site.urls),
    path('api/admin/media-upload/', upload_media_view, name='admin_media_upload'),

    # ── i18n language switcher (POST to /i18n/setlang/) ──────────────────────
    path('i18n/', include('django.conf.urls.i18n')),

    # ── API ───────────────────────────────────────────────────────────────────
    path('api/', include('presentation.api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── SEO ────────────────────────────────────────────────────────────────────
    # robots.txt cached 1 day (rarely changes, served on every crawl)
    path('robots.txt', cache_page(86400)(robots_txt), name='robots_txt'),
    # sitemap.xml cached 1 hour (fresh enough for crawlers, saves DB queries)
    path('sitemap.xml',
         cache_page(3600)(sitemap),
         {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),

    # ── Service Worker — emoji cache (root scope majburiy) ─────────────────
    path('sw.js', TemplateView.as_view(
        template_name='web/sw.js',
        content_type='application/javascript',
    ), name='service_worker'),

    # ── Health check ──────────────────────────────────────────────────────────
    path('health/', health_check, name='health_check'),

    # ── Static error pages for nginx error_page fallback ──────────────────────
    # nginx's `error_page 404 /404.html` makes a recursive request — without
    # these patterns it 404s in a loop and floods logs.
    path('404.html', custom_404_view, name='static_404'),
    path('500.html', custom_500_view, name='static_500'),

    # ── Telegram Bot Webhook ─────────────────────────────────────────────────
    path(
        'api/telegram/webhook/<str:secret>/',
        TelegramWebhookView.as_view(),
        name='telegram_webhook',
    ),
]

# Localized URLs — prefixed with /xo/, /uz/, /ru/, /en/. Default `xo` is also
# served at /xo/ (prefix_default_language=True), so existing /projects/ etc.
# now redirect to /xo/projects/.
urlpatterns += i18n_patterns(
    # Feeds (per-language RSS/Atom)
    path('blog/feed/', LatestPostsFeed(), name='blog_rss_feed'),
    path('blog/feed/atom/', LatestPostsAtomFeed(), name='blog_atom_feed'),

    # Interactions (Telegram auth, comments, likes) — language-aware
    path('', include('interactions.urls')),

    # Web (SSR) — home, projects, blog, contact, team, etc.
    path('', include('presentation.web.urls')),

    prefix_default_language=True,
)

# ── Custom error handlers ─────────────────────────────────────────────────────
# MUST be in ROOT_URLCONF — Django ignores these in included urlconfs.
handler404 = custom_404_view
handler500 = custom_500_view

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
