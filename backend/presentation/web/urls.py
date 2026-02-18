from django.urls import path
from .views import (
    HomeView, ProjectListView, ProjectDetailView,
    BlogListView, BlogDetailView, ContactView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('projects/', ProjectListView.as_view(), name='projects'),
    path('projects/<slug:slug>/', ProjectDetailView.as_view(), name='project_detail'),
    path('blog/', BlogListView.as_view(), name='blog_list'),
    path('blog/<slug:slug>/', BlogDetailView.as_view(), name='blog_detail'),
    path('contact/', ContactView.as_view(), name='contact'),
]
