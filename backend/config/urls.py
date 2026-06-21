import environ
from blog.feeds import LatestPostsAtomFeed, LatestPostsFeed
from core.emoji_views import emoji_manager
from core.sitemaps import SITEMAPS
from core.views import health_check, humans_txt, robots_txt, upload_media_view
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import index as sitemap_index
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from interactions.notifications.webhook import TelegramWebhookView
from presentation.web.views import TgAppRouterView, custom_404_view, custom_500_view
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

env = environ.Env()

# ── Admin URL: read from env, fall back to a non-obvious slug ─────────────────
ADMIN_URL = env('ADMIN_URL', default='admin/')

sitemaps = SITEMAPS

# Non-localized URLs (admin, API, sitemap, webhooks)
urlpatterns = [
    path(ADMIN_URL + 'telegram/settings/', emoji_manager, name='telegram_settings'),
    path(ADMIN_URL + 'rosetta/', include('rosetta.urls')),
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
    # humans.txt — E-E-A-T signal (real human team behind the site)
    path('humans.txt', cache_page(86400)(humans_txt), name='humans_txt'),
    # /sitemap.xml — sitemap-index pointing to per-section sub-sitemaps.
    # Search Console shows coverage per section; debug index issues per-segment.
    path('sitemap.xml',
         cache_page(3600)(sitemap_index),
         {'sitemaps': sitemaps, 'sitemap_url_name': 'sitemap_section'},
         name='sitemap_index'),
    path('sitemap-<section>.xml',
         cache_page(3600)(sitemap),
         {'sitemaps': sitemaps},
         name='sitemap_section'),

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

    # ── Telegram Mini App trampoline (NON-i18n on purpose) ───────────────────
    # Telegram delivers WebApp initData in the URL fragment (#tgWebAppData=…).
    # A 302 language-prefix redirect would drop that fragment → broken auto-login.
    # Keep this route prefix-free so it serves 200 directly (the trampoline then
    # reverse()s its localized target/login URLs itself).
    #
    # /app/ is the URL actually configured in @BotFather (menu button + Mini App);
    # /tg-app/ is the canonical name. Serve BOTH so every Telegram entry point
    # resolves without manual BotFather changes (was 404 → broken webview).
    path('tg-app/', TgAppRouterView.as_view(), name='tg_app'),
    path('app/', TgAppRouterView.as_view(), name='tg_app_alias'),
]

# ── Legacy URL redirects (pre-i18n migration) ─────────────────────────────────
# Before i18n, URLs were /xoprojects/, /rublog/ etc. (lang glued to page name).
# Now the correct format is /xo/projects/, /ru/blog/. 301 redirect to fix SEO.
from django.shortcuts import redirect as _redirect


def _make_legacy_redirect(lang, page):
    def _view_list(request):
        return _redirect(f'/{lang}/{page}/', permanent=True)

    def _view_detail(request, slug):
        return _redirect(f'/{lang}/{page}/{slug}/', permanent=True)

    return _view_list, _view_detail


for _lang in ('xo', 'uz', 'ru', 'en'):
    for _page in ('projects', 'blog', 'team', 'contact'):
        _vlist, _vdetail = _make_legacy_redirect(_lang, _page)
        urlpatterns += [
            re_path(rf'^{_lang}{_page}/$', _vlist),
            re_path(rf'^{_lang}{_page}/(?P<slug>[\w-]+)/$', _vdetail),
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
