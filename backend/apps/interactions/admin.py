from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import TelegramProfile, Comment, Like, CommentReaction


@admin.register(TelegramProfile)
class TelegramProfileAdmin(ModelAdmin):
    list_display  = ('user_card', 'username', 'created_at')
    search_fields = ('first_name', 'last_name', 'username', 'telegram_id')
    readonly_fields = ('telegram_id', 'first_name', 'last_name', 'username',
                       'photo_url', 'auth_date', 'created_at', 'updated_at')

    @admin.display(description='User')
    def user_card(self, obj):
        name = obj.display_name
        if obj.photo_url:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 10px;">'
                '<img src="{}" style="width: 28px; height: 28px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.1);">'
                '<span style="font-weight: 600;">{}</span>'
                '</div>',
                obj.photo_url, name
            )
        return name


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display   = ('author', 'short_text', 'parent', 'has_image', 'is_approved', 'is_reviewed', 'created_at')
    list_filter    = ('is_approved', 'is_reviewed', 'content_type', 'created_at')
    list_editable  = ('is_approved', 'is_reviewed')
    search_fields  = ('author__first_name', 'author__username', 'text')
    readonly_fields = ('author', 'content_type', 'object_id', 'created_at')
    ordering       = ('-created_at',)
    actions        = ['mark_as_reviewed', 'approve_comments', 'reject_comments']

    @admin.display(description='Text')
    def short_text(self, obj):
        return obj.text[:80] + ('…' if len(obj.text) > 80 else '')

    @admin.display(description='Img', boolean=True)
    def has_image(self, obj):
        return bool(obj.image)

    @admin.action(description='👀 Mark selected as Reviewed')
    def mark_as_reviewed(self, request, queryset):
        queryset.update(is_reviewed=True)

    @admin.action(description='✅ Approve (Make visible)')
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description='❌ Reject (Hide from site)')
    def reject_comments(self, request, queryset):
        queryset.update(is_approved=False)


@admin.register(CommentReaction)
class CommentReactionAdmin(ModelAdmin):
    list_display = ('comment', 'author', 'emoji', 'created_at')
    list_filter = ('emoji', 'created_at')


@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display  = ('author', 'content_type', 'object_id', 'created_at')
    list_filter   = ('content_type', 'created_at')
    readonly_fields = ('author', 'content_type', 'object_id', 'created_at')
