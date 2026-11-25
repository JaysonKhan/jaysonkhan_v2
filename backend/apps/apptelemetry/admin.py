"""Owner side of My Services: read-only installs/records, feedback inbox, LiveBridge dashboard.

The dashboard is an admin view (`admin_site.admin_view`), so it inherits the admin's staff login
and the admin IP allowlist like the other owner pages (UTM builder, asset manager).
"""
from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from unfold.admin import ModelAdmin

from .models import APP_LIVEBRIDGE, AppFeedback, AppInstall, TelemetryRecord
from .services import StatsService


class _ReadOnlyAdmin(ModelAdmin):
    """Rows are written by the app only; the owner may look and delete, never edit."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AppInstall)
class AppInstallAdmin(_ReadOnlyAdmin):
    list_display = ('short_id', 'app', 'app_version', 'os_version', 'ui_language', 'turns_count',
                    'first_seen', 'last_seen')
    list_filter = ('app', 'app_version', 'ui_language', 'last_seen')
    search_fields = ('install_id', 'app_version', 'os_version')
    ordering = ('-last_seen',)

    @admin.display(description='Install', ordering='install_id')
    def short_id(self, obj):
        return str(obj.install_id)[:8]


@admin.register(TelemetryRecord)
class TelemetryRecordAdmin(_ReadOnlyAdmin):
    list_display = ('type', 'install', 'session', 'direction', 'turn_id', 'e2e_ms', 'model', 'code',
                    'rating', 'app_version', 't', 'received_at')
    list_filter = ('type', 'direction', 'rating', 'model', 'code', 'app_version', 'received_at')
    search_fields = ('install__install_id', 'model', 'code')
    list_select_related = ('install',)
    show_full_result_count = False  # COUNT(*) over a large log on every page load
    ordering = ('-received_at',)

    def get_urls(self):
        return [
            path(
                'dashboard/',
                self.admin_site.admin_view(self.dashboard_view),
                name='apptelemetry_telemetryrecord_dashboard',
            ),
        ] + super().get_urls()

    def dashboard_view(self, request):
        stats = StatsService().owner_stats(APP_LIVEBRIDGE)
        charts = {
            'byDay': stats['by_day'],
            'byModel': stats['by_model'][:12],
            'byVersion': stats['by_version'][:12],
            'errors': stats['errors'][:15],
            'ratings': stats['ratings'],
        }
        context = {
            **self.admin_site.each_context(request),
            'title': 'LiveBridge',
            'stats': stats,
            'charts': charts,
            'opts': self.model._meta,
        }
        return render(request, 'admin/apptelemetry/dashboard.html', context)


@admin.register(AppFeedback)
class AppFeedbackAdmin(_ReadOnlyAdmin):
    list_display = ('preview', 'rating', 'app', 'app_version', 'ui_language', 'has_email', 'created_at')
    list_filter = ('app', 'rating', 'ui_language', 'app_version', 'created_at')
    search_fields = ('message', 'email')
    list_select_related = ('install',)
    ordering = ('-created_at',)

    @admin.display(description='Message')
    def preview(self, obj):
        text = ' '.join(obj.message.split())
        return text[:90] + ('…' if len(text) > 90 else '')

    @admin.display(description='E-mail', boolean=True)
    def has_email(self, obj):
        return bool(obj.email)
