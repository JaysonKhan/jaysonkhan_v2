from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from modeltranslation.admin import TranslationAdmin
from .models import Category, Tag, Post

from django import forms
from core.widgets import RichTextWidget
from django.utils.safestring import mark_safe

@admin.register(Category)
class CategoryAdmin(TranslationAdmin, UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name_xo',)}
    search_fields = ('name_xo', 'name_uz', 'name_ru', 'name_en')


@admin.register(Tag)
class TagAdmin(TranslationAdmin, UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name_xo',)}
    search_fields = ('name_xo', 'name_uz', 'name_ru', 'name_en')


class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = '__all__'
        widgets = {
            'content_rich_xo': RichTextWidget(),
            'content_rich_uz': RichTextWidget(),
            'content_rich_ru': RichTextWidget(),
            'content_rich_en': RichTextWidget(),
        }

@admin.register(Post)
class PostAdmin(TranslationAdmin, UnfoldModelAdmin):
    form = PostAdminForm
    list_per_page = 10
    list_display = ('thumbnail', 'title', 'category', 'is_published', 'created_at')
    list_display_links = ('thumbnail', 'title')
    list_filter = ('is_published', 'category', 'author')
    search_fields = ('title_xo', 'title_uz', 'title_ru', 'title_en')
    prepopulated_fields = {'slug': ('title_xo',)}
    filter_horizontal = ('tags',)

    def thumbnail(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" width="48" height="48" '
                'style="border-radius:8px;object-fit:cover;'
                'border:1px solid rgba(255,255,255,.12);" />',
                obj.featured_image.url,
            )
        return mark_safe(
            '<div style="width:48px;height:48px;border-radius:8px;'
            'background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);'
            'display:flex;align-items:center;justify-content:center;'
            'font-size:18px;">📝</div>'
        )
    thumbnail.short_description = ''
