from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
import environ
from presentation.web.views import custom_404_view, custom_500_view

env = environ.Env()

# ── Admin URL: read from env, fall back to a non-obvious slug ─────────────────
ADMIN_URL = env('ADMIN_URL', default='admin/')

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),

    # ── API ───────────────────────────────────────────────────────────────────
    path('api/', include('presentation.api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

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
