from blog.models import Category, Post, Tag
from contact.models import ContactMessage
from core.models import SiteSettings
from portfolio.models import Experience, Project, Skill
from rest_framework import serializers
from users.models import User


# Users
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'bio', 'profile_picture')


class PublicAuthorSerializer(serializers.ModelSerializer):
    """Display-safe author fields for public (AllowAny) endpoints. No email/PII."""
    class Meta:
        model = User
        fields = ('id', 'username', 'bio', 'profile_picture')


# Portfolio
class SkillSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Skill
        fields = '__all__'



class ProjectSerializer(serializers.ModelSerializer):
    technologies = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for infinite scroll list responses."""
    image_url = serializers.SerializerMethodField()
    tech_tags = serializers.SerializerMethodField()
    description = serializers.CharField(source='get_card_description', read_only=True)

    created_at = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'title', 'slug', 'description', 'image_url',
                  'tech_tags', 'created_at', 'is_featured',
                  'app_store_url', 'play_store_url', 'web_page_url',
                  'is_bot', 'github_url')

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return ''

    def get_tech_tags(self, obj):
        # Unsliced .all() consumes the prefetch cache; slice in Python (no extra query).
        return [t.name for t in list(obj.technologies.all())[:6]]


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
    author = PublicAuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ('id', 'title', 'slug', 'author', 'content_rich', 'excerpt',
                  'category', 'tags', 'featured_image', 'created_at',
                  'updated_at', 'reading_time')


class PostListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for infinite scroll list responses."""
    image_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', default='')
    created_at = serializers.DateTimeField(format='%b %d, %Y')

    class Meta:
        model = Post
        fields = ('id', 'title', 'slug', 'excerpt', 'image_url',
                  'category_name', 'created_at', 'reading_time')

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
        fields = ('id', 'name', 'email', 'subject', 'message', 'is_read', 'created_at')
        read_only_fields = ('id', 'created_at')


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
                   'resume_file', 'logo', 'created_at', 'updated_at',
                   # Owner PII / secret-ish: never echo back via the API.
                   'telegram_owner_id', 'telegram_admin_group_id',
                   'telegram_channel_id', 'google_site_verification',
                   'yandex_verification', 'bing_verification')

    def _url(self, field_value, request):
        if not field_value or not request:
            return None
        return request.build_absolute_uri(field_value.url)

    def get_favicon_url(self, obj):
        return self._url(obj.favicon, self.context.get('request'))

    def get_og_image_url(self, obj):
        return self._url(obj.og_image, self.context.get('request'))

    def get_hero_image_url(self, obj):
        return self._url(obj.hero_image, self.context.get('request'))

    def get_about_image_url(self, obj):
        return self._url(obj.about_image, self.context.get('request'))

    def get_resume_file_url(self, obj):
        return self._url(obj.resume_file, self.context.get('request'))
