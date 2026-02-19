from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for SiteSettings (singleton).
    Organized into logical fieldsets with image previews.
    """

    # Prevent adding multiple instances
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of the singleton."""
        return False

    readonly_fields = (
        'created_at',
        'updated_at',
        'favicon_preview',
        'logo_preview',
        'og_image_preview',
        'hero_image_preview',
        'about_image_preview',
        'resume_preview',
    )

    fieldsets = (
        ('Basic Settings', {
            'fields': ('site_title', 'site_tagline'),
        }),
        ('Branding', {
            'fields': ('favicon', 'favicon_preview', 'logo', 'logo_preview'),
            'classes': ('collapse',),
        }),
        ('SEO & Meta Tags', {
            'fields': (
                'meta_description',
                'meta_keywords',
                'og_url',
                'og_image',
                'og_image_preview',
            ),
            'description': 'Configure search engine and social media preview settings.',
        }),
        ('Hero Section', {
            'fields': (
                'hero_availability_badge',
                'hero_title',
                'hero_subtitle',
                'hero_image',
                'hero_image_preview',
            ),
        }),
        ('About Section', {
            'fields': (
                'about_title',
                'about_description',
                'about_image',
                'about_image_preview',
            ),
        }),
        ('Resume / CV', {
            'fields': (
                'resume_file',
                'resume_preview',
                'resume_button_text',
            ),
            'classes': ('collapse',),
        }),
        ('Contact & Social', {
            'fields': (
                'email',
                'github_url',
                'linkedin_url',
            ),
        }),
        ('Footer', {
            'fields': ('footer_text',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # Preview methods
    def favicon_preview(self, obj):
        if obj.favicon:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 4px;" />',
                obj.favicon.url
            )
        return "No favicon uploaded"
    favicon_preview.short_description = "Favicon Preview"

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="150" height="auto" style="border-radius: 4px;" />',
                obj.logo.url
            )
        return "No logo uploaded"
    logo_preview.short_description = "Logo Preview"

    def og_image_preview(self, obj):
        if obj.og_image:
            return format_html(
                '<img src="{}" width="300" height="auto" style="border-radius: 4px; max-height: 200px;" />',
                obj.og_image.url
            )
        return "No OG image uploaded"
    og_image_preview.short_description = "OG Image Preview"

    def hero_image_preview(self, obj):
        if obj.hero_image:
            return format_html(
                '<img src="{}" width="300" height="auto" style="border-radius: 4px; max-height: 200px;" />',
                obj.hero_image.url
            )
        return "No hero image uploaded"
    hero_image_preview.short_description = "Hero Image Preview"

    def about_image_preview(self, obj):
        if obj.about_image:
            return format_html(
                '<img src="{}" width="300" height="auto" style="border-radius: 4px; max-height: 200px;" />',
                obj.about_image.url
            )
        return "No about image uploaded"
    about_image_preview.short_description = "About Image Preview"

    def resume_preview(self, obj):
        if obj.resume_file:
            return format_html(
                '<a href="{}" target="_blank" class="button">📄 View Resume</a>',
                obj.resume_file.url
            )
        return "No resume uploaded"
    resume_preview.short_description = "Resume Preview"

    def changelist_view(self, request, extra_context=None):
        """Redirect to edit view if singleton exists."""
        obj = SiteSettings.objects.first()
        if obj:
            from django.shortcuts import redirect
            return redirect(f'admin:core_sitesettings_change', obj.pk)
        return super().changelist_view(request, extra_context)
