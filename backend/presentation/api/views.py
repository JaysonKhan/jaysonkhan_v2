from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (
    UserSerializer, SkillSerializer, ProjectSerializer,
    ExperienceSerializer, CategorySerializer, TagSerializer,
    PostSerializer, ContactMessageSerializer, SiteSettingsSerializer,
)
from users.models import User
from portfolio.models import Skill, Project, Experience
from blog.models import Category, Tag, Post
from contact.models import ContactMessage
from core.services import SiteSettingsService

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer

class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

class ExperienceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

class PostViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Post.objects.filter(is_published=True)
    serializer_class = PostSerializer

class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class SiteSettingsView(APIView):
    """
    GET /api/site-settings/
    Returns the singleton SiteSettings as JSON.
    Public endpoint — no auth required (read-only, no secrets exposed).
    Response served from cache; invalidated automatically on admin save.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        settings = SiteSettingsService.get()
        serializer = SiteSettingsSerializer(settings, context={"request": request})
        return Response(serializer.data)
