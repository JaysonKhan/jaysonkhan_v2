from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('subject', 'name', 'email', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
