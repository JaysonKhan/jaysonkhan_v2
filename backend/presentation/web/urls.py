from django.urls import path
from django.views.generic import TemplateView
from .views import (
    HomeView, ProjectListView, ProjectDetailView,
    BlogListView, BlogDetailView, ContactView,
    custom_404_view, custom_500_view,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('projects/', ProjectListView.as_view(), name='projects'),
    path('projects/<slug:slug>/', ProjectDetailView.as_view(), name='project_detail'),
    path('blog/', BlogListView.as_view(), name='blog_list'),
    path('blog/<slug:slug>/', BlogDetailView.as_view(), name='blog_detail'),
    path('contact/', ContactView.as_view(), name='contact'),
]

# Custom error handlers (active only when DEBUG=False)
handler404 = custom_404_view
handler500 = custom_500_view
