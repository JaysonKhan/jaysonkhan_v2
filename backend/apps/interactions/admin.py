from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    Comment, Like, CommentReaction,
    NotificationPreference, UserBan, AdminLogMessage,
)


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


# ── Notification & Moderation ────────────────────────────────────────────────

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = ('profile', 'replies_enabled', 'reactions_enabled')
    list_filter = ('replies_enabled', 'reactions_enabled')
    readonly_fields = ('profile',)


@admin.register(UserBan)
class UserBanAdmin(ModelAdmin):
    list_display = ('profile', 'ban_type', 'is_active', 'expires_at', 'created_at')
    list_filter = ('ban_type', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('profile__first_name', 'profile__username', 'reason')
    readonly_fields = ('profile', 'created_at')
    ordering = ('-created_at',)


@admin.register(AdminLogMessage)
class AdminLogMessageAdmin(ModelAdmin):
    list_display = ('message_id', 'profile', 'event_type', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('profile__first_name', 'profile__username', 'message_id')
    readonly_fields = ('message_id', 'profile', 'event_type', 'created_at')
    ordering = ('-created_at',)
