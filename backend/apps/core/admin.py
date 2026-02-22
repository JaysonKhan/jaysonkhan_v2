import logging
from django.contrib import admin
from django.db import connection
from django.shortcuts import redirect
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import SiteSettings

logger = logging.getLogger(__name__)


def _table_columns():
    """
    Return the set of column names that actually exist in the
    core_sitesettings table. Used to gracefully hide fields
    whose migration hasn't been applied yet.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM core_sitesettings LIMIT 0"
            )
            return {col[0] for col in cursor.description}
    except Exception:
        return set()


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    """
    Singleton admin for SiteSettings.
    - Add is blocked when a record already exists.
    - Delete is always blocked.
    - Changelist auto-redirects to the edit page.
    - Fieldsets auto-adapt if migration 0006 hasn't been applied yet.
    """

    # ── Permissions ───────────────────────────────────────────────────────────
    def has_add_permission(self, request):
        try:
            return not SiteSettings.objects.exists()
        except Exception:
            return True

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        try:
            obj = SiteSettings.objects.first()
            if obj:
                return redirect('admin:core_sitesettings_change', obj.pk)
        except Exception:
            pass
        return super().changelist_view(request, extra_context)

    # ── Read-only ─────────────────────────────────────────────────────────────
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

    # ── Dynamic fieldsets ─────────────────────────────────────────────────────
    def get_fieldsets(self, request, obj=None):
        columns = _table_columns()

        # ── Base fieldsets (always present) ────────────────────────────────
        fieldsets = [
            ('Branding', {
                'fields': (
                    'site_title',
                    'site_author',
                    'site_author_initials',
                    'site_tagline',
                    'favicon',
                    'favicon_preview',
                    'logo',
                    'logo_preview',
                ),
            }),
            ('SEO & Meta', {
                'fields': (
                    'meta_description',
                    'meta_keywords',
                    'og_url',
                    'og_image',
                    'og_image_preview',
                    'twitter_handle',
                ),
                'description': 'Controls Google snippets and social media link previews.',
            }),
        ]

        # ── Header / Navigation (requires migration 0006) ────────────────
        header_fields = ['nav_cta_text', 'nav_cta_url']
        if 'logo_text' in columns:
            header_fields.insert(0, 'logo_text')
        if 'nav_links_json' in columns:
            header_fields.append('nav_links_json')
        fieldsets.append(('Header / Navigation', {
            'fields': tuple(header_fields),
            'description': (
                'Customise the site header. '
                '"Logo text" overrides the author name in the navigation bar. '
                '"Extra nav links" is a JSON list for additional links '
                '(e.g. [{"label":"Resume","url":"/resume/"}]).'
            ),
        }))

        # ── Content sections (always present) ─────────────────────────────
        fieldsets.extend([
            ('Hero Section', {
                'fields': (
                    'hero_availability_badge',
                    'hero_title',
                    'hero_subtitle',
                    'hero_image',
                    'hero_image_preview',
                    'hero_primary_cta_text',
                    'hero_primary_cta_url',
                    'hero_secondary_cta_text',
                    'hero_secondary_cta_url',
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
            ('Skills Section', {
                'fields': ('skills_section_title',),
            }),
            ('Featured Projects Section', {
                'fields': (
                    'featured_projects_title',
                    'featured_projects_subtitle',
                ),
            }),
            ('Experience Section', {
                'fields': ('experience_section_title',),
            }),
            ('Visibility Controls', {
                'fields': ('apps_section_visible',),
                'description': (
                    'Toggle major site sections on/off. '
                    'Hiding a section removes its navigation link, footer link, '
                    'homepage content, and any hero CTAs pointing to it.'
                ),
            }),
            ('Blog Sections', {
                'fields': (
                    'latest_blog_title',
                    'blog_page_title',
                    'blog_page_subtitle',
                ),
            }),
            ('Projects Page', {
                'fields': (
                    'projects_page_title',
                    'projects_page_subtitle',
                ),
            }),
            ('Contact Page', {
                'fields': (
                    'contact_page_title',
                    'contact_page_subtitle',
                    'contact_email_label',
                    'contact_linkedin_label',
                ),
            }),
            ('Resume / CV', {
                'fields': (
                    'resume_file',
                    'resume_preview',
                    'resume_button_text',
                ),
            }),
            ('Contact Info & Socials', {
                'fields': (
                    'email',
                    'phone',
                    'github_url',
                    'linkedin_url',
                    'twitter_url',
                    'telegram_url',
                ),
            }),
        ])

        # ── Footer (requires migration 0006 for new fields) ──────────────
        footer_fields = []
        for fname in (
            'footer_description', 'footer_email',
            'footer_social_github', 'footer_social_linkedin',
            'footer_social_twitter', 'footer_social_telegram',
        ):
            if fname in columns:
                footer_fields.append(fname)
        footer_fields.append('footer_text')  # always exists

        fieldsets.append(('Footer', {
            'fields': tuple(footer_fields),
            'description': (
                'Footer-specific overrides. Leave blank to inherit from '
                'the main Contact Info & Socials section above.'
            ),
        }))

        fieldsets.append(('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }))

        return fieldsets

    # ── Preview helpers ───────────────────────────────────────────────────────
    def favicon_preview(self, obj):
        if obj.pk and obj.favicon:
            return format_html(
                '<img src="{}" width="48" height="48" '
                'style="border-radius:6px;border:1px solid rgba(255,255,255,.15);" />',
                obj.favicon.url,
            )
        return '—'
    favicon_preview.short_description = 'Preview'

    def logo_preview(self, obj):
        if obj.pk and obj.logo:
            return format_html(
                '<img src="{}" height="48" style="border-radius:6px;max-width:200px;" />',
                obj.logo.url,
            )
        return '—'
    logo_preview.short_description = 'Preview'

    def og_image_preview(self, obj):
        if obj.pk and obj.og_image:
            return format_html(
                '<img src="{}" style="max-width:320px;border-radius:8px;'
                'border:1px solid rgba(255,255,255,.15);" />',
                obj.og_image.url,
            )
        return '—'
    og_image_preview.short_description = 'Preview (1200x630)'

    def hero_image_preview(self, obj):
        if obj.pk and obj.hero_image:
            return format_html(
                '<img src="{}" style="max-width:300px;border-radius:12px;'
                'border:1px solid rgba(255,255,255,.15);" />',
                obj.hero_image.url,
            )
        return '—'
    hero_image_preview.short_description = 'Preview'

    def about_image_preview(self, obj):
        if obj.pk and obj.about_image:
            return format_html(
                '<img src="{}" style="max-width:300px;border-radius:12px;'
                'border:1px solid rgba(255,255,255,.15);" />',
                obj.about_image.url,
            )
        return '—'
    about_image_preview.short_description = 'Preview'

    def resume_preview(self, obj):
        if obj.pk and obj.resume_file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener" '
                'class="button">Open CV</a>',
                obj.resume_file.url,
            )
        return '—'
    resume_preview.short_description = 'File'
