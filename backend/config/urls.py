from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
import environ

env = environ.Env()

# ── Admin URL: read from env, fall back to a non-obvious slug ─────────────────
# Set ADMIN_URL=secret-panel/ in your .env to obscure the admin path.
# NEVER use the default 'admin/' in production.
ADMIN_URL = env('ADMIN_URL', default='admin/')

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),

    # ── API (all endpoints are admin-only by default via REST_FRAMEWORK settings) ──
    path('api/', include('presentation.api.urls')),
    # JWT token endpoints — these are behind IsAdminUser too (default permission)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── Web (SSR) ─────────────────────────────────────────────────────────────
    path('', include('presentation.web.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
