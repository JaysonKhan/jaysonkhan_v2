from rest_framework import serializers
from users.models import User
from portfolio.models import Skill, Project, Experience
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
    class Meta:
        model = Skill
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    technologies = SkillSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = '__all__'

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
