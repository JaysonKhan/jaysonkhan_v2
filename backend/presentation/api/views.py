from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (
    UserSerializer, SkillSerializer, ProjectSerializer, ProjectListSerializer,
    ExperienceSerializer, CategorySerializer, TagSerializer,
    PostSerializer, PostListSerializer, ContactMessageSerializer, SiteSettingsSerializer,
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
    queryset = Skill.objects.only('id', 'name', 'level', 'icon', 'category', 'order').all()
    serializer_class = SkillSerializer
    pagination_class = None  # Skills are always loaded fully


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProjectSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer

    def get_queryset(self):
        qs = (
            Project.objects
            .prefetch_related('technologies', 'screenshots')
            .order_by('order', '-created_at')
        )
        platform = self.request.query_params.get('platform')
        is_bot = self.request.query_params.get('is_bot')
        if is_bot:
            qs = qs.filter(is_bot=True)
        elif platform:
            qs = qs.filter(platform=platform)
        return qs


class ExperienceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer
    pagination_class = None  # Experience is always loaded fully


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PostSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        return PostSerializer

    def get_queryset(self):
        return (
            Post.objects
            .filter(is_published=True)
            .select_related('category', 'author')
            .prefetch_related('tags')
            .defer('content')
            .order_by('-created_at')
        )


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
