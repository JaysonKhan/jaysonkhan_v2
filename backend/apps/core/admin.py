import logging
from django.contrib import admin
from django.db import connection
from django.shortcuts import redirect
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import SiteSettings, PageView

logger = logging.getLogger(__name__)


def _table_columns() -> set:
    """
    Return column names that exist in core_sitesettings.
    Used to gracefully skip fields whose migration hasn't run yet.
    Falls back to an empty set so the admin still loads without crashing.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM core_sitesettings LIMIT 0")
            return {col[0] for col in cursor.description}
    except Exception as exc:
        logger.warning("Could not introspect core_sitesettings columns: %s", exc)
        return set()


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    """
    Singleton admin for SiteSettings — tab-based layout.

    Tabs:
      1. Branding         — site identity, logo, favicon
      2. SEO & Meta       — meta tags, OG image, Twitter card
      3. Navigation       — header links and CTA button
      4. Homepage         — hero, about, section headings, visibility
      5. Pages            — per-page titles/subtitles
      6. Contact & Socials — email, social URLs, CV/resume
      7. Footer           — footer overrides
      8. System           — timestamps (read-only)
    """

    # ── Permissions ────────────────────────────────────────────────────────────
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

    # ── Read-only fields ───────────────────────────────────────────────────────
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

    # ── Tab fieldsets ──────────────────────────────────────────────────────────
    def get_fieldsets(self, request, obj=None):
        columns = _table_columns()

        # Navigation tab: add optional columns if migration applied
        nav_fields = ['nav_cta_text', 'nav_cta_url']
        if 'logo_text' in columns:
            nav_fields.insert(0, 'logo_text')
        if 'nav_links_json' in columns:
            nav_fields.append('nav_links_json')

        # Footer tab: add optional columns if migration applied
        footer_fields = []
        for fname in (
            'footer_description', 'footer_email',
            'footer_social_github', 'footer_social_linkedin',
            'footer_social_twitter', 'footer_social_telegram',
        ):
            if fname in columns:
                footer_fields.append(fname)
        footer_fields.append('footer_text')   # always exists

        return [

            # ── Tab 1: Branding ────────────────────────────────────────────────
            ('Branding', {
                'classes': ('tab',),
                'description': (
                    'Core site identity — name, author, tagline, logo and favicon.'
                ),
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

            # ── Tab 2: SEO & Meta ──────────────────────────────────────────────
            ('SEO & Meta', {
                'classes': ('tab',),
                'description': (
                    'Controls Google snippet, Open Graph preview and Twitter card.'
                ),
                'fields': (
                    'meta_description',
                    'meta_keywords',
                    'og_url',
                    'og_image',
                    'og_image_preview',
                    'twitter_handle',
                ),
            }),

            # ── Tab 3: Navigation ──────────────────────────────────────────────
            ('Navigation', {
                'classes': ('tab',),
                'description': (
                    'Header bar settings. '
                    '"Logo text" overrides the author name in the navbar. '
                    '"Extra nav links" accepts a JSON list, '
                    'e.g. [{"label":"Resume","url":"/resume/"}].'
                ),
                'fields': tuple(nav_fields),
            }),

            # ── Tab 4: Homepage ────────────────────────────────────────────────
            ('Homepage', {
                'classes': ('tab',),
                'description': (
                    'Hero banner, About section, section headings, and '
                    'visibility toggles for homepage blocks.'
                ),
                'fields': (
                    # — Hero ——————————————————————————————————————————————————
                    'hero_availability_badge',
                    'hero_title',
                    'hero_subtitle',
                    'hero_image',
                    'hero_image_preview',
                    'hero_primary_cta_text',
                    'hero_primary_cta_url',
                    'hero_secondary_cta_text',
                    'hero_secondary_cta_url',
                    # — About ——————————————————————————————————————————————————
                    'about_title',
                    'about_description',
                    'about_image',
                    'about_image_preview',
                    # — Stats Bar ——————————————————————————————————————————————
                    'stat_1_count', 'stat_1_suffix', 'stat_1_label',
                    'stat_2_count', 'stat_2_suffix', 'stat_2_label',
                    'stat_3_count', 'stat_3_suffix', 'stat_3_label',
                    'stat_4_count', 'stat_4_suffix', 'stat_4_label',
                    # — Section headings ——————————————————————————————————————
                    'skills_section_title',
                    'featured_projects_title',
                    'featured_projects_subtitle',
                    'experience_section_title',
                    'latest_blog_title',
                    # — Visibility ————————————————————————————————————————————
                    'apps_section_visible',
                ),
            }),

            # ── Tab 5: Pages ───────────────────────────────────────────────────
            ('Pages', {
                'classes': ('tab',),
                'description': (
                    'Per-page <h1> headings and sub-headings for Apps, Blog '
                    'and Contact pages.'
                ),
                'fields': (
                    # — Apps / Projects ———————————————————————————————————————
                    'projects_page_title',
                    'projects_page_subtitle',
                    # — Blog ———————————————————————————————————————————————————
                    'blog_page_title',
                    'blog_page_subtitle',
                    # — Contact ————————————————————————————————————————————————
                    'contact_page_title',
                    'contact_page_subtitle',
                    'contact_email_label',
                    'contact_linkedin_label',
                ),
            }),

            # ── Tab 6: Contact & Socials ────────────────────────────────────────
            ('Contact & Socials', {
                'classes': ('tab',),
                'description': (
                    'Primary email, phone, social profile URLs, and '
                    'CV/resume file used across the whole site.'
                ),
                'fields': (
                    'email',
                    'phone',
                    'github_url',
                    'linkedin_url',
                    'twitter_url',
                    'telegram_url',
                    'resume_file',
                    'resume_preview',
                    'resume_button_text',
                ),
            }),

            # ── Tab 7: Footer ──────────────────────────────────────────────────
            ('Footer', {
                'classes': ('tab',),
                'description': (
                    'Footer-specific overrides. '
                    'Leave any field blank to inherit from Contact & Socials.'
                ),
                'fields': tuple(footer_fields),
            }),

            # ── Tab 8: System ──────────────────────────────────────────────────
            ('System', {
                'classes': ('tab',),
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            }),
        ]

    # ── Image / file preview helpers ───────────────────────────────────────────

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
    og_image_preview.short_description = 'Preview (1200×630)'

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


@admin.register(PageView)
class PageViewAdmin(ModelAdmin):
    list_display = ('visitor_id', 'ip_address', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('visitor_id', 'ip_address', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
