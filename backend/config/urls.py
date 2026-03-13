from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
import environ
from presentation.web.views import custom_404_view, custom_500_view
from core.views import upload_media_view, robots_txt
from core.sitemaps import StaticViewSitemap, ProjectSitemap, PostSitemap

env = environ.Env()

# ── Admin URL: read from env, fall back to a non-obvious slug ─────────────────
ADMIN_URL = env('ADMIN_URL', default='admin/')

sitemaps = {
    'static': StaticViewSitemap,
    'projects': ProjectSitemap,
    'posts': PostSitemap,
}

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('api/admin/media-upload/', upload_media_view, name='admin_media_upload'),

    # ── API ───────────────────────────────────────────────────────────────────
    path('api/', include('presentation.api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── SEO ────────────────────────────────────────────────────────────────────
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),

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
