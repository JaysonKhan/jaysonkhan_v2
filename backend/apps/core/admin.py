import logging
from django.contrib import admin, messages
from django.db import connection
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from unfold.admin import ModelAdmin

from .models import SiteSettings, PageView, Asset

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

            # ── Tab 2b: Analytics ──────────────────────────────────────────────
            ('Analytics', {
                'classes': ('tab',),
                'description': (
                    'Tracking snippets — Google Analytics 4 and Yandex Metrica. '
                    'Leave empty to disable the tracker.'
                ),
                'fields': (
                    'google_analytics_id',
                    'yandex_metrika_id',
                ),
            }),

            # ── Tab 2c: Search Console Verification ────────────────────────────
            ('Search Console verification', {
                'classes': ('tab',),
                'description': (
                    'Verification tokens for Google Search Console, Yandex Webmaster '
                    'and Bing Webmaster. Paste only the content= value of the meta tag.'
                ),
                'fields': (
                    'google_site_verification',
                    'yandex_verification',
                    'bing_verification',
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
                    'hero_title',
                    'hero_subtitle',
                    'hero_image',
                    'hero_image_preview',
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
                    'featured_projects_title',
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

            # ── Tab v3: Editorial content ──────────────────────────────────────
            ('v3 · Editorial', {
                'classes': ('tab',),
                'description': (
                    'All v3 (cream+black editorial) site copy. JSON fields accept lists '
                    'of {n, title, description} dicts (manifesto/process) or {title, description} '
                    'dicts (team_values), or simple string lists (ticker_items). Leave a JSON '
                    'field empty to use seed defaults.'
                ),
                'fields': tuple(self._editorial_fields(columns)),
            }),

            # ── Tab 8: System ──────────────────────────────────────────────────
            # Telegram settings managed at /admin/telegram/settings/
            ('System', {
                'classes': ('tab',),
                'fields': (
                    'created_at',
                    'updated_at',
                ),
            }),
        ]

    @staticmethod
    def _editorial_fields(columns):
        """Return v3 editorial fields that exist in the DB schema (graceful migration)."""
        candidates = [
            'availability_badge',
            'hero_eyebrow', 'hero_volume_label', 'hero_location',
            'hero_scroll_label', 'hero_section_count',
            'brand_tagline', 'footer_volume',
            'ticker_items',
            'manifesto_eyebrow', 'manifesto_title', 'manifesto_label', 'manifesto_principles',
            'metrics_eyebrow', 'metrics_title', 'metrics_description',
            'process_eyebrow', 'process_title', 'process_steps',
            'cta_eyebrow', 'cta_title_pre', 'cta_title_em', 'cta_description',
            'cta_button_text', 'cta_response_label',
            'contact_form_label', 'contact_form_title',
            'contact_availability_status', 'contact_availability_note',
            'team_hero_eyebrow', 'team_section_label', 'team_studio_label', 'team_intro',
            'team_values_eyebrow', 'team_values_title', 'team_values_intro', 'team_values',
        ]
        return [f for f in candidates if not columns or f in columns]

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


@admin.register(Asset)
class AssetAdmin(ModelAdmin):
    """Editorial Asset Manager — replaces standard changelist with grid + drag-drop."""

    list_display = ('thumbnail', 'name', 'folder', 'format', 'size_human_col', 'dimensions', 'uploaded_at')
    list_display_links = ('thumbnail', 'name')
    list_filter = ('folder', 'format', 'uploaded_at')
    search_fields = ('name', 'alt_text')
    readonly_fields = ('format', 'size_bytes', 'width', 'height', 'uploaded_at', 'updated_at', 'preview_large')

    fieldsets = (
        ('File', {
            'fields': ('file', 'preview_large', 'name', 'folder', 'alt_text'),
        }),
        ('Metadata', {
            'fields': ('format', 'size_bytes', 'width', 'height', 'uploaded_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_urls(self):
        return [
            path(
                'manager/',
                self.admin_site.admin_view(self.asset_manager_view),
                name='core_asset_manager',
            ),
            path(
                'manager/upload/',
                self.admin_site.admin_view(self.asset_upload),
                name='core_asset_upload',
            ),
            path(
                'manager/bulk/',
                self.admin_site.admin_view(self.asset_bulk),
                name='core_asset_bulk',
            ),
        ] + super().get_urls()

    def asset_manager_view(self, request):
        """Editorial Asset Manager — the visual replacement for the changelist."""
        folder = request.GET.get('folder', 'all')
        qs = Asset.objects.all()
        if folder != 'all':
            qs = qs.filter(folder=folder)

        total_size = Asset.objects.aggregate(total=Sum('size_bytes'))['total'] or 0
        total_count = Asset.objects.count()

        folders = [{'key': 'all', 'label': 'All', 'count': total_count}]
        for key, label in Asset.FOLDER_CHOICES:
            folders.append({
                'key': key,
                'label': label,
                'count': Asset.objects.filter(folder=key).count(),
            })

        latest = Asset.objects.order_by('-uploaded_at').first()
        from django.utils import timezone
        from .dashboard import _humanize
        last_upload = _humanize(timezone.now() - latest.uploaded_at) if latest else '—'

        context = {
            **self.admin_site.each_context(request),
            'title': 'Asset Manager',
            'assets': qs,
            'folders': folders,
            'active_folder': folder,
            'total_size_mb': round(total_size / 1024 / 1024, 1),
            'total_count': total_count,
            'last_upload': last_upload,
            'opts': self.model._meta,
        }
        return render(request, 'admin/core/asset_manager.html', context)

    def asset_upload(self, request):
        """Drag-drop upload endpoint — returns JSON with new asset metadata."""
        if request.method != 'POST':
            return HttpResponseBadRequest("POST only")
        if not (request.user.is_staff and request.user.is_active):
            return JsonResponse({'error': 'forbidden'}, status=403)

        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'error': 'no files'}, status=400)

        folder = request.POST.get('folder', 'misc')
        if folder not in dict(Asset.FOLDER_CHOICES):
            folder = 'misc'

        created = []
        for f in files:
            asset = Asset(file=f, folder=folder)
            asset.save()
            created.append({
                'id': asset.pk,
                'asset_id': asset.asset_id,
                'name': asset.name,
                'format': asset.format,
                'size': asset.size_human,
                'dimensions': asset.dimensions,
                'folder': asset.folder,
                'url': asset.file.url,
                'is_image': asset.is_image,
            })
        return JsonResponse({'status': 'ok', 'created': created})

    def asset_bulk(self, request):
        """Bulk delete / move endpoint."""
        if request.method != 'POST':
            return HttpResponseBadRequest("POST only")
        if not (request.user.is_staff and request.user.is_active):
            return JsonResponse({'error': 'forbidden'}, status=403)

        action = request.POST.get('action')
        ids = [int(x) for x in request.POST.getlist('ids') if x.isdigit()]
        if not ids:
            return JsonResponse({'error': 'no ids'}, status=400)

        qs = Asset.objects.filter(pk__in=ids)

        if action == 'delete':
            count = qs.count()
            for a in qs:
                try:
                    a.file.delete(save=False)
                except Exception:
                    pass
            qs.delete()
            return JsonResponse({'status': 'ok', 'deleted': count})

        if action == 'move':
            target = request.POST.get('folder', 'misc')
            if target not in dict(Asset.FOLDER_CHOICES):
                return JsonResponse({'error': 'bad folder'}, status=400)
            n = qs.update(folder=target)
            return JsonResponse({'status': 'ok', 'moved': n, 'folder': target})

        return JsonResponse({'error': 'unknown action'}, status=400)

    def thumbnail(self, obj):
        if obj.is_image and obj.file:
            try:
                return format_html(
                    '<img src="{}" width="48" height="48" '
                    'style="border-radius:4px;object-fit:cover;'
                    'border:1px solid var(--jk-line-2,rgba(20,18,14,.14));" />',
                    obj.file.url,
                )
            except Exception:
                pass
        return format_html(
            '<div style="width:48px;height:48px;border-radius:4px;'
            'background:var(--jk-bg-3,#e6dfd0);border:1px solid var(--jk-line-2,rgba(20,18,14,.14));'
            'display:flex;align-items:center;justify-content:center;'
            'font-family:Fraunces,serif;font-style:italic;font-size:18px;'
            'color:var(--jk-fg-3,#6b665d);">{}</div>',
            (obj.format or '?')[:1],
        )
    thumbnail.short_description = ''

    def size_human_col(self, obj):
        return obj.size_human
    size_human_col.short_description = 'Size'

    def preview_large(self, obj):
        if obj.is_image and obj.file:
            try:
                return format_html(
                    '<img src="{}" style="max-width:520px;max-height:340px;'
                    'border:1px solid var(--jk-line-2,rgba(20,18,14,.14));" />',
                    obj.file.url,
                )
            except Exception:
                pass
        return '—'
    preview_large.short_description = 'Preview'
