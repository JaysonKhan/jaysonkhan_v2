from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
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

urlpatterns = [
    path(ADMIN_URL + 'telegram/settings/', emoji_manager, name='telegram_settings'),
    path(ADMIN_URL + 'bot/', include('botproxy.urls')),
    path(ADMIN_URL + 'osint/', include('osint.urls')),
    path(ADMIN_URL, admin.site.urls),
    path('api/admin/media-upload/', upload_media_view, name='admin_media_upload'),

    # ── API ───────────────────────────────────────────────────────────────────
    path('api/', include('presentation.api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── SEO & Feeds ────────────────────────────────────────────────────────────
    # robots.txt cached 1 day (rarely changes, served on every crawl)
    path('robots.txt', cache_page(86400)(robots_txt), name='robots_txt'),
    # sitemap.xml cached 1 hour (fresh enough for crawlers, saves DB queries)
    path('sitemap.xml',
         cache_page(3600)(sitemap),
         {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('blog/feed/', LatestPostsFeed(), name='blog_rss_feed'),
    path('blog/feed/atom/', LatestPostsAtomFeed(), name='blog_atom_feed'),

    # ── Service Worker — emoji cache (root scope majburiy) ─────────────────
    path('sw.js', TemplateView.as_view(
        template_name='web/sw.js',
        content_type='application/javascript',
    ), name='service_worker'),

    # ── Health check ──────────────────────────────────────────────────────────
    path('health/', health_check, name='health_check'),

    # ── Telegram Bot Webhook ─────────────────────────────────────────────────
    path(
        'api/telegram/webhook/<str:secret>/',
        TelegramWebhookView.as_view(),
        name='telegram_webhook',
    ),

    # ── Interactions (Telegram auth, comments, likes) — included at root ─────
    path('', include('interactions.urls')),

    # ── Web (SSR) ─────────────────────────────────────────────────────────────
    path('', include('presentation.web.urls')),
]

# ── Custom error handlers ─────────────────────────────────────────────────────
# MUST be in ROOT_URLCONF — Django ignores these in included urlconfs.
handler404 = custom_404_view
handler500 = custom_500_view

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
