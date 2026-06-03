from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('subject', 'name', 'email', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    # is_read is intentionally NOT in readonly_fields so it can be toggled.
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
    actions = ('mark_as_read', 'mark_as_unread')

    @admin.action(description='Mark selected as read')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='Mark selected as unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
