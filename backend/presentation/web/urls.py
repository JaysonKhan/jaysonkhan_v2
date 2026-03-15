from django.urls import path
from .views import (
    HomeView, ProjectListView, ProjectDetailView,
    BlogListView, BlogDetailView, BlogSearchView, ContactView,
    TgAppRouterView,
)

urlpatterns = [
    path('tg-app/', TgAppRouterView.as_view(), name='tg_app'),
    path('', HomeView.as_view(), name='home'),
    path('projects/', ProjectListView.as_view(), name='projects'),
    path('projects/<slug:slug>/', ProjectDetailView.as_view(), name='project_detail'),
    path('blog/', BlogListView.as_view(), name='blog_list'),
    path('blog/search/', BlogSearchView.as_view(), name='blog_search'),
    path('blog/<slug:slug>/', BlogDetailView.as_view(), name='blog_detail'),
    path('contact/', ContactView.as_view(), name='contact'),
]
