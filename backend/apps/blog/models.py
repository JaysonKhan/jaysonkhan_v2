import math

from core.utils import sanitize_rich_text
from django.conf import settings
from django.db import models
from django.utils.html import strip_tags


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_posts')
    content_rich = models.TextField(blank=True, null=True, help_text="Rich text content (HTML)")
    excerpt = models.TextField(max_length=500, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    featured_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_published', '-created_at'],
                         name='post_published_date'),
            models.Index(fields=['slug', 'is_published'],
                         name='post_slug_published'),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog_detail', kwargs={'slug': self.slug})

    @property
    def reading_time(self):
        """Estimated reading time in minutes (avg 200 wpm)."""
        text = strip_tags(self.content_rich or '')
        word_count = len(text.split())
        return max(1, math.ceil(word_count / 200))

    def save(self, *args, **kwargs):
        for lang_code in ('xo', 'uz', 'ru', 'en'):
            field = f'content_rich_{lang_code}'
            val = getattr(self, field, None)
            if val:
                setattr(self, field, sanitize_rich_text(val))
        super().save(*args, **kwargs)
