from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, SkillViewSet, ProjectViewSet,
    ExperienceViewSet, CategoryViewSet, TagViewSet,
    PostViewSet, ContactMessageViewSet, SiteSettingsView,
)

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
    path('site-settings/', SiteSettingsView.as_view(), name='site-settings'),
]
