from django.urls import path

from .views import (
    BlogDetailView,
    BlogListView,
    BlogSearchView,
    ContactView,
    GalleryFeedView,
    HomeView,
    ProjectDetailView,
    ProjectListView,
    TeamView,
)

# NOTE: tg-app/ (Telegram Mini App trampoline) is intentionally registered
# in config/urls.py OUTSIDE i18n_patterns — a language-prefix 302 redirect
# would drop Telegram's #tgWebAppData fragment and break initData auto-login.

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('gallery/feed/', GalleryFeedView.as_view(), name='gallery_feed'),
    path('projects/', ProjectListView.as_view(), name='projects'),
    path('projects/<slug:slug>/', ProjectDetailView.as_view(), name='project_detail'),
    path('blog/', BlogListView.as_view(), name='blog_list'),
    path('blog/search/', BlogSearchView.as_view(), name='blog_search'),
    path('blog/<slug:slug>/', BlogDetailView.as_view(), name='blog_detail'),
    path('team/', TeamView.as_view(), name='team'),
    path('contact/', ContactView.as_view(), name='contact'),
]
