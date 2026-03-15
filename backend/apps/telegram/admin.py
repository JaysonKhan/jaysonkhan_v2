"""Admin configuration for unified Telegram entities."""
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import EntitySource, TelegramEntity, TelegramSession


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
        url = obj.get_photo_url()
        if url:
            return format_html(
                '<div style="display:flex;align-items:center;gap:10px;">'
                '<img src="{}" style="width:28px;height:28px;border-radius:50%;'
                'border:1px solid rgba(255,255,255,0.1);"'
                ' onerror="this.style.display=\'none\'">'
                '<span style="font-weight:600;">{}</span>'
                "</div>",
                url,
                name,
            )
        return name

    @admin.display(description="Telegram ID")
    def tg_id_link(self, obj):
        """Telegram ID → OSINT profil link."""
        try:
            url = reverse("osint_profile", kwargs={"user_id": obj.telegram_id})
            return format_html(
                '<a href="{}" title="OSINT profil">{}</a>',
                url,
                obj.telegram_id,
            )
        except Exception:
            return obj.telegram_id

    @admin.display(description="Services")
    def services_display(self, obj):
        """Qaysi servislardan topilgan."""
        sources = obj.sources.all()
        if not sources:
            return "-"
        badges = []
        colors = {
            "site": "#3b82f6",
            "osint": "#f59e0b",
            "rektor": "#10b981",
            "ovoz": "#8b5cf6",
        }
        for src in sources:
            color = colors.get(src.service, "#6b7280")
            badges.append(
                f'<span style="background:{color};color:#fff;padding:2px 8px;'
                f'border-radius:10px;font-size:11px;font-weight:600;">'
                f"{src.get_service_display()}</span>"
            )
        return format_html(" ".join(badges))

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("sources")


@admin.register(TelegramSession)
class TelegramSessionAdmin(ModelAdmin):
    list_display = ("account_name", "account_id", "updated_at")
    readonly_fields = ("session_string", "account_id", "account_name", "created_at", "updated_at")

    def has_add_permission(self, request):
        """Singleton — faqat bitta yozuv."""
        try:
            return not TelegramSession.objects.exists()
        except Exception:
            return True

    def has_delete_permission(self, request, obj=None):
        return False
