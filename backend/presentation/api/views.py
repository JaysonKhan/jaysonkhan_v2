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
    """Admin-only: user list must never be public."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Inherits IsAdminUser from REST_FRAMEWORK default


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Skill.objects.only('id', 'name', 'level', 'icon', 'category', 'order').all()
    serializer_class = SkillSerializer
    pagination_class = None
    # Inherits IsAdminUser from REST_FRAMEWORK default


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProjectSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer

    def get_queryset(self):
        qs = (
            Project.objects
            .filter(is_visible=True)
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
    # Inherits IsAdminUser from REST_FRAMEWORK default


class ExperienceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer
    pagination_class = None
    # Inherits IsAdminUser from REST_FRAMEWORK default


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None
    # Inherits IsAdminUser from REST_FRAMEWORK default


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    # Inherits IsAdminUser from REST_FRAMEWORK default


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
    # Inherits IsAdminUser from REST_FRAMEWORK default


class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    POST (create) is open to anyone — the public contact form.
    All other actions (list, retrieve, update, delete) require admin.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class SiteSettingsView(APIView):
    """
    Admin-only. The SSR templates already have all site settings via
    context_processors — there is no legitimate public use case for this endpoint.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        site_settings = SiteSettingsService.get()
        serializer = SiteSettingsSerializer(site_settings, context={"request": request})
        return Response(serializer.data)
