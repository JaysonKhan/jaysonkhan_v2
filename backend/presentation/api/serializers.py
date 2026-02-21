from rest_framework import serializers
from users.models import User
from portfolio.models import Skill, Project, ProjectScreenshot, Experience
from blog.models import Category, Tag, Post
from contact.models import ContactMessage
from core.models import SiteSettings


# Users
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'bio', 'profile_picture')


# Portfolio
class SkillSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Skill
        fields = '__all__'


class ProjectScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectScreenshot
        fields = ('id', 'image', 'caption', 'order')


class ProjectSerializer(serializers.ModelSerializer):
    technologies = SkillSerializer(many=True, read_only=True)
    screenshots = ProjectScreenshotSerializer(many=True, read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)

    class Meta:
        model = Project
        fields = '__all__'


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for infinite scroll list responses."""
    image_url = serializers.SerializerMethodField()
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    tech_tags = serializers.SerializerMethodField()
    description = serializers.CharField(source='get_card_description', read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'title', 'slug', 'description', 'image_url',
                  'platform', 'platform_display', 'tech_tags',
                  'app_store_url', 'play_store_url', 'github_url')

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return ''

    def get_tech_tags(self, obj):
        return [t.name for t in obj.technologies.all()[:6]]


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = '__all__'


# Blog
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = '__all__'


class PostListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for infinite scroll list responses."""
    image_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', default='')
    created_at = serializers.DateTimeField(format='%b %d, %Y')

    class Meta:
        model = Post
        fields = ('id', 'title', 'slug', 'excerpt', 'image_url',
                  'category_name', 'created_at')

    def get_image_url(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return ''


# Contact
class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'


# Site Settings
class SiteSettingsSerializer(serializers.ModelSerializer):
    """
    Read-only public serializer for SiteSettings.
    Exposes resolved media URLs for favicon, og_image, hero/about images.
    Excludes internal timestamps from public response.
    """
    favicon_url = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    about_image_url = serializers.SerializerMethodField()
    resume_file_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        exclude = ('favicon', 'og_image', 'hero_image', 'about_image',
                   'resume_file', 'logo', 'created_at', 'updated_at')

    def _url(self, field_value, request):
        if not field_value:
            return None
        return request.build_absolute_uri(field_value.url)

    def get_favicon_url(self, obj):
        return self._url(obj.favicon, self.context['request'])

    def get_og_image_url(self, obj):
        return self._url(obj.og_image, self.context['request'])

    def get_hero_image_url(self, obj):
        return self._url(obj.hero_image, self.context['request'])

    def get_about_image_url(self, obj):
        return self._url(obj.about_image, self.context['request'])

    def get_resume_file_url(self, obj):
        return self._url(obj.resume_file, self.context['request'])
