from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import TelegramProfile, Comment, Like


@admin.register(TelegramProfile)
class TelegramProfileAdmin(ModelAdmin):
    list_display  = ('telegram_id', 'full_name', 'username', 'created_at')
    search_fields = ('first_name', 'last_name', 'username', 'telegram_id')
    readonly_fields = ('telegram_id', 'first_name', 'last_name', 'username',
                       'photo_url', 'auth_date', 'created_at', 'updated_at')


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display   = ('author', 'short_text', 'content_type', 'object_id',
                      'is_approved', 'created_at')
    list_filter    = ('is_approved', 'content_type', 'created_at')
    list_editable  = ('is_approved',)
    search_fields  = ('author__first_name', 'author__username', 'text')
    readonly_fields = ('author', 'content_type', 'object_id', 'created_at')
    ordering       = ('-created_at',)
    actions        = ['approve_comments', 'reject_comments']

    @admin.display(description='Text')
    def short_text(self, obj):
        return obj.text[:80] + ('…' if len(obj.text) > 80 else '')

    @admin.action(description='✅ Approve selected comments')
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description='❌ Reject (unapprove) selected comments')
    def reject_comments(self, request, queryset):
        queryset.update(is_approved=False)


@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display  = ('author', 'content_type', 'object_id', 'created_at')
    list_filter   = ('content_type', 'created_at')
    readonly_fields = ('author', 'content_type', 'object_id', 'created_at')
