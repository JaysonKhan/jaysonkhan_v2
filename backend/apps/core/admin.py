import logging

from django.contrib import admin
from django.db import connection
from django.db.models import Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html
from modeltranslation.admin import TranslationAdmin
from unfold.admin import ModelAdmin

from .models import (
    Asset,
    PageView,
    SiteSettings,
    SiteSettingsBranding,
    SiteSettingsContact,
    SiteSettingsEditorial,
    SiteSettingsEmoji,
    SiteSettingsHomepage,
    SiteSettingsNavigation,
    SiteSettingsSEO,
    SiteSettingsTelegram,
)

logger = logging.getLogger(__name__)


def _table_columns() -> set:
    """Return column names from core_sitesettings — graceful fallback."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM core_sitesettings LIMIT 0")
            return {col[0] for col in cursor.description}
    except Exception as exc:
        logger.warning("Could not introspect core_sitesettings columns: %s", exc)
        return set()


# ── Shared image preview helpers ─────────────────────────────────────────────

class _ImagePreviewMixin:
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
                '<a href="{}" target="_blank" rel="noopener" class="button">Open CV</a>',
                obj.resume_file.url,
            )
        return '—'
    resume_preview.short_description = 'File'


# ── Common proxy admin mixin ─────────────────────────────────────────────────

class _ProxySettingsMixin:
    """Singleton redirect + no-add / no-delete for all SiteSettings proxy admins."""

    def has_add_permission(self, request):
        try:
            return not SiteSettings.objects.exists()
        except Exception:
            return True

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.objects.first()
        if obj:
            model_name = self.model._meta.model_name
            return redirect(f'admin:core_{model_name}_change', obj.pk)
        return super().changelist_view(request, extra_context)


# ── 1. Brending ──────────────────────────────────────────────────────────────

@admin.register(SiteSettingsBranding)
class SiteSettingsBrandingAdmin(
    _ProxySettingsMixin, _ImagePreviewMixin, TranslationAdmin, ModelAdmin
):
    readonly_fields = ('favicon_preview', 'logo_preview')

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Brending — sayt identifikatsiyasi', {
                'classes': ('tab',),
                'description': 'Sayt nomi, muallif, taglayn, logo va favicon.',
                'fields': (
                    'site_title',
                    'site_author',
                    'site_author_initials',
                    'site_tagline',
                    'favicon', 'favicon_preview',
                    'logo', 'logo_preview',
                ),
            }),
        ]
        return self._patch_fieldsets(fieldsets)


# ── 2. SEO & Analitika ───────────────────────────────────────────────────────

@admin.register(SiteSettingsSEO)
class SiteSettingsSEOAdmin(
    _ProxySettingsMixin, _ImagePreviewMixin, TranslationAdmin, ModelAdmin
):
    readonly_fields = ('og_image_preview',)

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('SEO & Meta teglari', {
                'classes': ('tab',),
                'description': 'Google snippet, Open Graph preview va Twitter card.',
                'fields': (
                    'meta_description',
                    'meta_keywords',
                    'og_url',
                    'og_image', 'og_image_preview',
                    'twitter_handle',
                ),
            }),
            ('Analitika', {
                'classes': ('tab',),
                'description': "GA4 va Yandex Metrica. Bo'sh qoldirish — o'chirib qo'yadi.",
                'fields': (
                    'google_analytics_id',
                    'yandex_metrika_id',
                ),
            }),
            ('Search Console tekshiruvi', {
                'classes': ('tab',),
                'description': 'Faqat content= qiymatini kiriting (to\'liq meta teg emas).',
                'fields': (
                    'google_site_verification',
                    'yandex_verification',
                    'bing_verification',
                ),
            }),
        ]
        return self._patch_fieldsets(fieldsets)


# ── 3. Navigatsiya & Footer ──────────────────────────────────────────────────

@admin.register(SiteSettingsNavigation)
class SiteSettingsNavigationAdmin(
    _ProxySettingsMixin, TranslationAdmin, ModelAdmin
):
    def get_fieldsets(self, request, obj=None):
        columns = _table_columns()
        nav_fields = ['nav_cta_text', 'nav_cta_url']
        if not columns or 'logo_text' in columns:
            nav_fields.insert(0, 'logo_text')
        if not columns or 'nav_links_json' in columns:
            nav_fields.append('nav_links_json')

        footer_fields = []
        for fname in (
            'footer_description', 'footer_social_github', 'footer_social_linkedin',
            'footer_social_twitter', 'footer_social_telegram',
        ):
            if not columns or fname in columns:
                footer_fields.append(fname)
        footer_fields.append('footer_text')

        fieldsets = [
            ('Navigatsiya', {
                'classes': ('tab',),
                'description': 'Header — logo matni, CTA tugmasi, qo\'shimcha havolalar.',
                'fields': tuple(nav_fields),
            }),
            ('Footer', {
                'classes': ('tab',),
                "description": "Footer-ga xos sozlamalar. Bo'sh qoldirish — Aloqa bo'limidan meros oladi.",
                'fields': tuple(footer_fields),
            }),
        ]
        return self._patch_fieldsets(fieldsets)


# ── 4. Bosh sahifa ───────────────────────────────────────────────────────────

@admin.register(SiteSettingsHomepage)
class SiteSettingsHomepageAdmin(
    _ProxySettingsMixin, _ImagePreviewMixin, TranslationAdmin, ModelAdmin
):
    readonly_fields = ('hero_image_preview', 'about_image_preview', 'resume_preview')

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Hero banneri', {
                'classes': ('tab',),
                'fields': (
                    'hero_title',
                    'hero_subtitle',
                    'hero_image', 'hero_image_preview',
                ),
            }),
            ("About bo'limi", {
                'classes': ('tab',),
                'fields': (
                    'about_title',
                    'about_description',
                    'about_image', 'about_image_preview',
                ),
            }),
            ('Statistika paneli', {
                'classes': ('tab',),
                'description': '4 ta statistika — counter animatsiyasi bilan ko\'rsatiladi.',
                'fields': (
                    'stat_1_count', 'stat_1_suffix', 'stat_1_label',
                    'stat_2_count', 'stat_2_suffix', 'stat_2_label',
                    'stat_3_count', 'stat_3_suffix', 'stat_3_label',
                    'stat_4_count', 'stat_4_suffix', 'stat_4_label',
                ),
            }),
            ("Bo'lim sarlavhalari", {
                'classes': ('tab',),
                'fields': (
                    'featured_projects_title',
                    'apps_section_visible',
                ),
            }),
            ('Sahifa sarlavhalari', {
                'classes': ('tab',),
                'description': 'Apps, Blog va Aloqa sahifalarining <h1> sarlavhalari.',
                'fields': (
                    'projects_page_title', 'projects_page_subtitle',
                    'blog_page_title', 'blog_page_subtitle',
                    'contact_page_title', 'contact_page_subtitle',
                    'resume_file', 'resume_preview', 'resume_button_text',
                ),
            }),
        ]
        return self._patch_fieldsets(fieldsets)


# ── 5. Aloqa & Ijtimoiy ──────────────────────────────────────────────────────

@admin.register(SiteSettingsContact)
class SiteSettingsContactAdmin(_ProxySettingsMixin, ModelAdmin):
    fieldsets = (
        ("Aloqa ma'lumotlari", {
            'fields': ('email', 'phone'),
        }),
        ('Ijtimoiy tarmoqlar', {
            'fields': ('github_url', 'linkedin_url', 'twitter_url', 'telegram_url'),
        }),
    )


# ── 6. Telegram Bot ──────────────────────────────────────────────────────────

@admin.register(SiteSettingsTelegram)
class SiteSettingsTelegramAdmin(_ProxySettingsMixin, ModelAdmin):
    fieldsets = (
        ('Bot konfiguratsiyasi', {
            'description': 'Owner ID va guruh ID — /id buyrug\'i bilan aniqlash mumkin.',
            'fields': (
                'telegram_owner_id',
                'telegram_admin_group_id',
                'telegram_channel_id',
            ),
        }),
        ('Bildirishnomalar', {
            'description': 'Qaysi hodisalar admin guruhiga yuborilsin.',
            'fields': (
                'admin_notify_new_users',
                'admin_notify_comments',
                'admin_notify_replies',
                'admin_notify_reactions',
                'admin_notify_likes',
                'admin_notify_contacts',
            ),
        }),
    )


# ── 7. Emoji sozlamalari ─────────────────────────────────────────────────────

@admin.register(SiteSettingsEmoji)
class SiteSettingsEmojiAdmin(_ProxySettingsMixin, ModelAdmin):
    fieldsets = (
        ('Asosiy havolalar', {
            'description': 'Blog post va loyiha xabarlari uchun tugma emojilari.',
            'fields': (
                'tg_emoji_read_more', 'tg_emoji_google_play', 'tg_emoji_app_store',
                'tg_emoji_web', 'tg_emoji_bot', 'tg_emoji_github', 'tg_emoji_comment',
            ),
        }),
        ('Server Monitor', {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_server', 'tg_emoji_cpu', 'tg_emoji_ram', 'tg_emoji_disk',
                'tg_emoji_ok', 'tg_emoji_warn', 'tg_emoji_critical',
                'tg_emoji_chart', 'tg_emoji_alert', 'tg_emoji_money', 'tg_emoji_clock',
                'tg_emoji_uptime', 'tg_emoji_load', 'tg_emoji_swap',
                'tg_emoji_services_icon', 'tg_emoji_trophy',
                'tg_emoji_nginx', 'tg_emoji_postgresql',
                'tg_emoji_package', 'tg_emoji_upgrade', 'tg_emoji_downgrade',
            ),
        }),
        ('Bildirishnomalar', {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_reply', 'tg_emoji_like', 'tg_emoji_unlike',
                'tg_emoji_contact_msg', 'tg_emoji_user', 'tg_emoji_returning',
                'tg_emoji_premium', 'tg_emoji_osint', 'tg_emoji_education', 'tg_emoji_group',
            ),
        }),
        ('OSINT', {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_channel_icon', 'tg_emoji_id_badge', 'tg_emoji_phone',
                'tg_emoji_sources', 'tg_emoji_crown', 'tg_emoji_verified',
                'tg_emoji_scam_warn', 'tg_emoji_history', 'tg_emoji_pencil', 'tg_emoji_calendar',
            ),
        }),
        ('Buyruqlar', {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_greeting', 'tg_emoji_ban', 'tg_emoji_mute', 'tg_emoji_lock',
                'tg_emoji_notifications_icon', 'tg_emoji_config_icon',
                'tg_emoji_error', 'tg_emoji_success',
                'tg_emoji_backup_icon', 'tg_emoji_logs_icon',
            ),
        }),
        ('Kanal ulashish', {
            'classes': ('collapse',),
            'fields': ('tg_emoji_post', 'tg_emoji_project', 'tg_emoji_tech'),
        }),
        ('Bot holati & Harakatlar', {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_warning', 'tg_emoji_red_dot', 'tg_emoji_green_dot', 'tg_emoji_blocked',
                'tg_emoji_plus', 'tg_emoji_minus', 'tg_emoji_edit', 'tg_emoji_right_arrow',
            ),
        }),
        ('Bot navigatsiya & Mukofotlar', {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_point_right', 'tg_emoji_point_down', 'tg_emoji_back', 'tg_emoji_home',
                'tg_emoji_gold', 'tg_emoji_silver', 'tg_emoji_bronze',
            ),
        }),
        ("Odamlar & Muloqot", {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_person', 'tg_emoji_people', 'tg_emoji_teacher',
                'tg_emoji_crown_icon', 'tg_emoji_eye',
                'tg_emoji_mail', 'tg_emoji_upload', 'tg_emoji_email_icon',
                'tg_emoji_phone_icon', 'tg_emoji_thought', 'tg_emoji_speech',
            ),
        }),
        ("Ma'lumot & Tizim", {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_stats', 'tg_emoji_growth', 'tg_emoji_document',
                'tg_emoji_name_badge', 'tg_emoji_mobile', 'tg_emoji_device', 'tg_emoji_numbers',
                'tg_emoji_settings', 'tg_emoji_secure', 'tg_emoji_locked',
                'tg_emoji_key', 'tg_emoji_shield', 'tg_emoji_cloud',
            ),
        }),
        ('Turli', {
            'classes': ('collapse',),
            'fields': (
                'tg_emoji_globe', 'tg_emoji_moon', 'tg_emoji_clover', 'tg_emoji_target',
                'tg_emoji_diamond', 'tg_emoji_control', 'tg_emoji_fire', 'tg_emoji_triangle',
                'tg_emoji_graduation', 'tg_emoji_pray', 'tg_emoji_school', 'tg_emoji_ballot',
                'tg_emoji_blue_square', 'tg_emoji_lightning', 'tg_emoji_celebration',
                'tg_emoji_memo', 'tg_emoji_pin', 'tg_emoji_undo', 'tg_emoji_skip',
            ),
        }),
        ("Qo'shimcha (JSON)", {
            'classes': ('collapse',),
            'fields': ('tg_emoji_extra',),
        }),
    )


# ── 8. Editorial v3 ──────────────────────────────────────────────────────────

@admin.register(SiteSettingsEditorial)
class SiteSettingsEditorialAdmin(
    _ProxySettingsMixin, TranslationAdmin, ModelAdmin
):
    def get_fieldsets(self, request, obj=None):
        columns = _table_columns()
        ok = lambda f: not columns or f in columns

        def tab(title, *fields, description=None):
            visible = tuple(f for f in fields if ok(f))
            if not visible:
                return None
            opts = {'classes': ('tab',), 'fields': visible}
            if description:
                opts['description'] = description
            return (title, opts)

        fieldsets = [
            tab('Hero & Brend',
                'availability_badge',
                'hero_eyebrow', 'hero_volume_label', 'hero_location',
                'hero_scroll_label', 'hero_section_count',
                'brand_tagline', 'footer_volume',
                'ticker_items',
            ),
            tab('Manifesto',
                'manifesto_eyebrow', 'manifesto_title', 'manifesto_label', 'manifesto_principles',
            ),
            tab('Metriks',
                'metrics_eyebrow', 'metrics_title', 'metrics_description',
            ),
            tab('Jarayon',
                'process_eyebrow', 'process_title', 'process_steps',
            ),
            tab('CTA',
                'cta_eyebrow', 'cta_title_pre', 'cta_title_em',
                'cta_description', 'cta_button_text', 'cta_response_label',
            ),
            tab("Aloqa bo'limi",
                'contact_form_label', 'contact_form_title',
                'contact_availability_status', 'contact_availability_note',
                'contact_section_label', 'contact_section_channels',
            ),
            tab("Jamoa bo'limi",
                'team_hero_eyebrow', 'team_hero_headline',
                'team_section_label', 'team_studio_label', 'team_intro',
                'team_values_eyebrow', 'team_values_title', 'team_values_intro', 'team_values',
            ),
            tab('Footer CTA',
                'footer_cta_eyebrow', 'footer_cta_headline', 'footer_practice_items',
            ),
            tab('Xato sahifalari',
                'error_404_headline', 'error_404_description',
                'error_500_headline', 'error_500_description',
                'error_unavailable_headline', 'error_unavailable_description',
            ),
            tab("Bo'lim teglari",
                'about_section_eyebrow',
                'projects_section_label',
                'blog_section_label', 'blog_section_status',
            ),
        ]
        fieldsets = [fs for fs in fieldsets if fs is not None]
        return self._patch_fieldsets(fieldsets)


# ── PageView ─────────────────────────────────────────────────────────────────

@admin.register(PageView)
class PageViewAdmin(ModelAdmin):
    list_display = ('source_badge', 'landing_path', 'utm_campaign', 'referrer_short', 'ip_address', 'created_at')
    list_filter = ('source', 'created_at', 'utm_source')
    search_fields = ('referrer', 'landing_path', 'utm_source', 'utm_medium', 'utm_campaign', 'ip_address')
    readonly_fields = (
        'visitor_id', 'ip_address', 'created_at', 'source', 'landing_path',
        'referrer', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content',
        'utm_term', 'user_agent',
    )
    ordering = ('-created_at',)

    @admin.display(description='Source', ordering='source')
    def source_badge(self, obj):
        from core.tracking import source_color
        label = obj.source or 'direct'
        color = source_color(label)
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:6px;font-size:11px;'
            'font-weight:600;letter-spacing:.04em;text-transform:uppercase;">'
            '<span style="width:8px;height:8px;border-radius:50%;background:{};"></span>{}</span>',
            color, label,
        )

    @admin.display(description='Referrer')
    def referrer_short(self, obj):
        if not obj.referrer:
            return '—'
        r = obj.referrer.replace('https://', '').replace('http://', '')
        return format_html('<span title="{}">{}</span>', obj.referrer,
                           r[:42] + ('…' if len(r) > 42 else ''))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ── Asset ─────────────────────────────────────────────────────────────────────

@admin.register(Asset)
class AssetAdmin(TranslationAdmin, ModelAdmin):
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
