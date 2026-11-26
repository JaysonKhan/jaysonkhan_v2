from django.urls import path

from .account_views import (
    account_buy,
    account_connect,
    account_delete,
    account_device_sign_out,
    account_page,
    account_purchase_done,
    account_sign_out,
)
from .views import (
    AboutView,
    BlogDetailView,
    BlogListView,
    BlogSearchView,
    ContactView,
    GalleryFeedView,
    HomeView,
    LiveBridgeStatsView,
    ProjectDetailView,
    ProjectListView,
    ServicesIndexView,
    TeamView,
    VoiceAgentDemoView,
)

# NOTE: tg-app/ (Telegram Mini App trampoline) is intentionally registered
# in config/urls.py OUTSIDE i18n_patterns — a language-prefix 302 redirect
# would drop Telegram's #tgWebAppData fragment and break initData auto-login.

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('gallery/feed/', GalleryFeedView.as_view(), name='gallery_feed'),
    path('projects/', ProjectListView.as_view(), name='projects'),
    path('projects/<slug:slug>/', ProjectDetailView.as_view(), name='project_detail'),
    path('blog/', BlogListView.as_view(), name='blog_list'),
    path('blog/search/', BlogSearchView.as_view(), name='blog_search'),
    path('blog/<slug:slug>/', BlogDetailView.as_view(), name='blog_detail'),
    path('team/', TeamView.as_view(), name='team'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('demos/voice-agent/', VoiceAgentDemoView.as_view(), name='voice_agent_demo'),
    # My Services (apps/apptelemetry). The LiveBridge app links to the bare /services/livebridge/;
    # LocaleMiddleware redirects it to the visitor's language prefix.
    path('services/', ServicesIndexView.as_view(), name='services'),
    path('services/livebridge/', LiveBridgeStatsView.as_view(), name='services_livebridge'),
    # LiveBridge accounts (apps/livebridge) — Google sign-in lives outside i18n_patterns in config/urls.py
    path('account/', account_page, name='account'),
    path('account/connect/', account_connect, name='account_connect'),
    path('account/buy/<slug:code>/', account_buy, name='account_buy'),
    path('account/purchase/done/', account_purchase_done, name='account_purchase_done'),
    path('account/devices/<int:pk>/sign-out/', account_device_sign_out, name='account_device_sign_out'),
    path('account/delete/', account_delete, name='account_delete'),
    path('account/sign-out/', account_sign_out, name='account_sign_out'),
]
