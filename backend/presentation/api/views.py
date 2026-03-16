import json

from rest_framework import viewsets, permissions, status
from rest_framework.authentication import SessionAuthentication
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
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer

    def get_queryset(self):
        qs = (
            Project.objects
            .filter(is_visible=True)
            .prefetch_related('technologies')
            .order_by('order', '-created_at')
        )
        # URL-based filtering — mirrors ProjectListView logic.
        f = self.request.query_params.get('filter', '')
        if f == 'cross':
            qs = qs.filter(play_store_url__gt='', app_store_url__gt='')
        elif f == 'android':
            qs = qs.filter(play_store_url__gt='')
        elif f == 'ios':
            qs = qs.filter(app_store_url__gt='')
        elif f == 'web':
            qs = qs.filter(web_page_url__gt='')
        elif f == 'bot':
            qs = qs.filter(is_bot=True)
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
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        return PostSerializer

    def get_queryset(self):
        qs = (
            Post.objects
            .filter(is_published=True)
            .select_related('category', 'author')
            .prefetch_related('tags')
            .order_by('-created_at')
        )
        # Defer heavy HTML field on list (not needed for cards);
        # detail view needs it for full content rendering.
        if self.action == 'list':
            qs = qs.defer('content_rich')
        return qs
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


class ShareToChannelView(APIView):
    """
    POST /api/share-to-channel/
    Body: {"content_type": "post"|"project", "slug": "the-slug"}

    Shares a blog post or project to the configured Telegram channel.
    Admin-only, session-authenticated (called from SSR detail pages).
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        content_type = request.data.get('content_type')
        slug = request.data.get('slug')

        if not content_type or not slug:
            return Response(
                {'status': 'error', 'error': 'content_type va slug talab qilinadi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from interactions.notifications.channel_share import ChannelShareService
        service = ChannelShareService()

        if content_type == 'post':
            try:
                obj = Post.objects.get(slug=slug, is_published=True)
            except Post.DoesNotExist:
                return Response(
                    {'status': 'error', 'error': 'Post topilmadi.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            success, message = service.share_post(obj, user=request.user)

        elif content_type == 'project':
            try:
                obj = Project.objects.get(slug=slug, is_visible=True)
            except Project.DoesNotExist:
                return Response(
                    {'status': 'error', 'error': 'Project topilmadi.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            success, message = service.share_project(obj, user=request.user)

        else:
            return Response(
                {'status': 'error', 'error': 'content_type "post" yoki "project" bo\'lishi kerak.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if success:
            info = service.get_share_info(obj)
            return Response({
                'status': 'ok',
                'message': message,
                'shared_at': info['shared_at'].isoformat() if info and info['shared_at'] else None,
            })
        return Response(
            {'status': 'error', 'error': message},
            status=status.HTTP_400_BAD_REQUEST,
        )
