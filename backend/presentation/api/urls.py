from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, SkillViewSet, ProjectViewSet,
    ExperienceViewSet, CategoryViewSet, TagViewSet,
    PostViewSet, ContactMessageViewSet, SiteSettingsView,
    ShareToChannelView,
)
from .livebridge_views import (
    CheckoutView,
    DeviceStartView,
    DeviceTokenView,
    LogoutView,
    MeView,
    PackagesView,
    TokenRefreshView,
)
from .services_views import FeedbackView, TelemetryIngestView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'skills', SkillViewSet)
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'experience', ExperienceViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'tags', TagViewSet)
router.register(r'posts', PostViewSet, basename='post')
router.register(r'contact', ContactMessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # My Services (apptelemetry) — public ingestion for the owner's open-source apps
    path('services/v1/telemetry/', TelemetryIngestView.as_view(), name='services_telemetry'),
    path('services/v1/feedback/', FeedbackView.as_view(), name='services_feedback'),
    # LiveBridge accounts (apps/livebridge) — the desktop app's API, bearer tokens
    path('livebridge/v1/device/start/', DeviceStartView.as_view(), name='livebridge_device_start'),
    path('livebridge/v1/device/token/', DeviceTokenView.as_view(), name='livebridge_device_token'),
    path('livebridge/v1/token/refresh/', TokenRefreshView.as_view(), name='livebridge_token_refresh'),
    path('livebridge/v1/logout/', LogoutView.as_view(), name='livebridge_logout'),
    path('livebridge/v1/me/', MeView.as_view(), name='livebridge_me'),
    path('livebridge/v1/packages/', PackagesView.as_view(), name='livebridge_packages'),
    path('livebridge/v1/checkout/', CheckoutView.as_view(), name='livebridge_checkout'),
    path('site-settings/', SiteSettingsView.as_view(), name='site-settings'),
    path('share-to-channel/', ShareToChannelView.as_view(), name='share-to-channel'),
]
