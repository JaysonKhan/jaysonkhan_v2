"""Admin configuration for unified Telegram entities."""
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin, TabularInline

from .models import EntitySource, TelegramEntity


class EntitySourceInline(TabularInline):
    model = EntitySource
    extra = 0
    readonly_fields = ("service", "role", "extra_data", "first_seen_at", "updated_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TelegramEntity)
class TelegramEntityAdmin(ModelAdmin):
    list_display = (
        "user_card",
        "entity_type",
        "tg_id_link",
        "username",
        "services_display",
        "updated_at",
    )
    list_filter = ("entity_type", "sources__service", "has_photo", "is_premium", "is_verified")
    search_fields = ("first_name", "last_name", "username", "telegram_id")
    readonly_fields = (
        "telegram_id", "entity_type",
        "first_name", "last_name", "username", "title",
        "phone", "bio",
        "photo_preview", "photo_url", "photo_file", "photo_fetched_at", "has_photo",
        "auth_date",
        "is_verified", "is_premium", "is_scam", "is_fake",
        "created_at", "updated_at",
    )
    inlines = [EntitySourceInline]

    fieldsets = [
        ("Identity", {
            "fields": (
                "telegram_id", "entity_type",
                "first_name", "last_name", "username", "title",
                "phone", "bio",
            ),
        }),
        ("Photo", {
            "fields": ("photo_preview", "photo_url", "photo_file", "photo_fetched_at", "has_photo"),
        }),
        ("Metadata", {
            "fields": ("auth_date", "is_verified", "is_premium", "is_scam", "is_fake"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    ]

    @admin.display(description="Photo")
    def photo_preview(self, obj):
        """Show avatar from photo_url (universal — photo service yoki Login Widget)."""
        url = obj.get_photo_url()
        if url:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;border-radius:50%;'
                'border:2px solid rgba(255,255,255,0.15);object-fit:cover;"'
                ' onerror="this.style.display=\'none\'">',
                url,
            )
        return format_html(
            '<div style="width:80px;height:80px;border-radius:50%;'
            'background:rgba(255,255,255,0.08);display:flex;align-items:center;'
            'justify-content:center;font-size:28px;font-weight:700;color:rgba(255,255,255,0.4);">'
            '{}</div>',
            (obj.first_name or "?")[:1].upper(),
        )

    @admin.display(description="User")
    def user_card(self, obj):
        name = obj.display_name
        letter = (obj.first_name or obj.title or name or "?")[:1].upper()
        url = obj.get_photo_url()
        if url:
            return format_html(
                '<div style="display:flex;align-items:center;gap:10px;">'
                '<img src="{}" style="width:28px;height:28px;border-radius:50%;'
                'border:1px solid rgba(255,255,255,0.1);"'
                ' onerror="this.style.display=\'none\';'
                'this.nextElementSibling.style.display=\'flex\'">'
                '<div style="display:none;width:28px;height:28px;border-radius:50%;'
                'background:rgba(99,102,241,0.25);align-items:center;justify-content:center;'
                'font-size:13px;font-weight:700;color:rgba(255,255,255,0.7);'
                'flex-shrink:0;">{}</div>'
                '<span style="font-weight:600;">{}</span>'
                "</div>",
                url,
                letter,
                name,
            )
        return format_html(
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<div style="width:28px;height:28px;border-radius:50%;'
            'background:rgba(99,102,241,0.25);display:flex;align-items:center;'
            'justify-content:center;font-size:13px;font-weight:700;'
            'color:rgba(255,255,255,0.7);flex-shrink:0;">{}</div>'
            '<span style="font-weight:600;">{}</span>'
            "</div>",
            letter,
            name,
        )

    @admin.display(description="Telegram ID")
    def tg_id_link(self, obj):
        """Telegram ID → t.me link (if username available)."""
        if obj.username:
            url = f"https://t.me/{obj.username}"
            return format_html(
                '<a href="{}" title="Telegram" target="_blank" rel="noopener">{}</a>',
                url,
                obj.telegram_id,
            )
        return obj.telegram_id

    @admin.display(description="Services")
    def services_display(self, obj):
        """Qaysi servislardan topilgan."""
        sources = obj.sources.all()
        if not sources:
            return "-"
        colors = {
            "site": "#3b82f6",
            "osint": "#f59e0b",
            "talabaovozi": "#10b981",
        }
        # format_html_join escapes each dynamic value AND is valid on every
        # Django version (a bare format_html(joined) 500s on Django 5+ with
        # "args or kwargs must be provided").
        return format_html_join(
            " ",
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            (
                (colors.get(src.service, "#6b7280"), src.get_service_display())
                for src in sources
            ),
        )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("sources")


