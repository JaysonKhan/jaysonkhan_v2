"""
Admin surface for Ops (cron monitoring).

Two models, two pages:
    * `ManagedCron` — catalog (command + schedule).
      Each row has a "Run now" action that spawns the `cron_run` wrapper
      in a detached subprocess, so the admin UI doesn't block.
    * `CronRun` — execution history with colour-coded status pills.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin as UnfoldAdmin
from unfold.decorators import action, display

from ops.models import CronRun, CronStatus, ManagedCron


STATUS_COLOR = {
    CronStatus.RUNNING: 'info',
    CronStatus.SUCCESS: 'success',
    CronStatus.FAILED: 'danger',
}


def _manage_py_path() -> Path:
    candidate = Path(settings.BASE_DIR) / 'manage.py'
    if candidate.exists():
        return candidate
    cwd = Path.cwd() / 'manage.py'
    if cwd.exists():
        return cwd
    return candidate


def _spawn_cron_run(target: str, *, triggered_by: str = 'admin') -> None:
    python = sys.executable
    manage_py = _manage_py_path()
    cmd = [
        python, str(manage_py), 'cron_run', target,
        f'--triggered-by={triggered_by}',
    ]
    # The gunicorn unit ships PATH=<venv>/bin only — extend it with the
    # system locations so the spawned process can resolve helpers like
    # `systemctl` (used by service_health_check). Without this the
    # admin "Run now" path would fall back to "no-systemctl" for every
    # unit and produce a phantom DOWN/UP storm on the next cron tick.
    child_env = {**os.environ}
    child_env['PATH'] = (
        child_env.get('PATH', '') + ':/usr/bin:/bin:/usr/sbin:/sbin'
    ).lstrip(':')
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        cwd=str(manage_py.parent),
        env=child_env,
    )


@admin.register(ManagedCron)
class ManagedCronAdmin(UnfoldAdmin):
    list_display = (
        'command', 'category', 'schedule_display',
        'last_run_display', 'success_rate_7d',
        'enabled_badge', 'run_now_button',
    )
    list_filter = ('category', 'enabled')
    search_fields = ('command', 'verbose_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Buyruq', {
            'fields': ('command', 'verbose_name', 'description', 'category'),
        }),
        ('Jadval', {
            'fields': ('schedule', 'enabled'),
        }),
        ('Meta', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    actions_detail = ('run_now_detail',)

    @display(description='Jadval')
    def schedule_display(self, obj: ManagedCron) -> str:
        if not obj.schedule:
            return format_html('<span style="color:#999">—</span>')
        return format_html('<code>{}</code>', obj.schedule)

    @display(description="So\u2019nggi yurish")
    def last_run_display(self, obj: ManagedCron) -> str:
        run = (
            CronRun.objects.filter(command=obj.command)
            .order_by('-started_at').first()
        )
        if not run:
            return format_html('<span style="color:#999">hech qachon</span>')
        colors = {
            'success': '#16a34a', 'failed': '#dc2626', 'running': '#2563eb',
        }
        color = colors.get(run.status, '#666')
        delta = timezone.now() - run.started_at
        ago = _humanize_delta(delta)
        url = reverse('admin:ops_cronrun_change', args=[run.pk])
        return format_html(
            '<a href="{}" style="color:{};font-weight:600">\u25cf</a> '
            '<a href="{}">{} \u00b7 {}</a>',
            url, color, url, ago, run.duration_display or '\u2014',
        )

    @display(description='Muvaffaqiyat (7 kun)')
    def success_rate_7d(self, obj: ManagedCron) -> str:
        since = timezone.now() - timedelta(days=7)
        runs = CronRun.objects.filter(command=obj.command, started_at__gte=since)
        total = runs.count()
        if total == 0:
            return format_html('<span style="color:#999">\u2014</span>')
        ok = runs.filter(status=CronStatus.SUCCESS).count()
        pct = ok * 100 // total
        color = '#16a34a' if pct >= 95 else '#f59e0b' if pct >= 70 else '#dc2626'
        return format_html(
            '<span style="color:{};font-weight:600">{}%</span> '
            '<span style="color:#999;font-size:11px">({}/{})</span>',
            color, pct, ok, total,
        )

    @display(description='Holat')
    def enabled_badge(self, obj: ManagedCron) -> str:
        if obj.enabled:
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:2px 8px;'
                'border-radius:10px;font-size:11px;font-weight:600">YOQILGAN</span>'
            )
        return format_html(
            '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:600">O\u02bcCHIRILGAN</span>'
        )

    @display(description='Amallar')
    def run_now_button(self, obj: ManagedCron) -> str:
        if not obj.enabled:
            return format_html('<span style="color:#999">\u2014</span>')
        url = reverse('admin:ops_managedcron_run_now', args=[obj.pk])
        return format_html(
            '<a href="{}" class="button" style="background:#2563eb;color:#fff;'
            'padding:4px 12px;border-radius:6px;font-size:12px;'
            'text-decoration:none">\u25b6 Hoziroq</a>', url,
        )

    def get_urls(self):
        base = super().get_urls()
        return [
            path(
                '<int:pk>/run-now/',
                self.admin_site.admin_view(self.run_now_view),
                name='ops_managedcron_run_now',
            ),
        ] + base

    def run_now_view(self, request, pk: int):
        try:
            cron = ManagedCron.objects.get(pk=pk)
        except ManagedCron.DoesNotExist:
            messages.error(request, 'Cron topilmadi.')
            return HttpResponseRedirect(reverse('admin:ops_managedcron_changelist'))

        if not cron.enabled:
            messages.warning(request, f'{cron.command} \u2014 o\u02bcchirilgan.')
            return HttpResponseRedirect(
                reverse('admin:ops_managedcron_change', args=[pk])
            )

        try:
            _spawn_cron_run(cron.command, triggered_by='admin')
            messages.success(
                request,
                f'{cron.command} fon rejimida ishga tushirildi.',
            )
        except OSError as e:
            messages.error(request, f'Ishga tushirib bo\u02bcmadi: {e}')

        return HttpResponseRedirect(
            reverse('admin:ops_cronrun_changelist') + f'?command={cron.command}'
        )

    @action(description='\u25b6 Hoziroq ishga tushirish', url_path='run-now-detail')
    def run_now_detail(self, request, object_id):
        return self.run_now_view(request, int(object_id))


@admin.register(CronRun)
class CronRunAdmin(UnfoldAdmin):
    list_display = (
        'command', 'status_badge', 'started_at_display',
        'duration_display_col', 'triggered_by_display',
        'error_preview',
    )
    list_filter = ('status', 'command', 'triggered_by')
    search_fields = ('command', 'stdout', 'stderr', 'error_summary')
    readonly_fields = (
        'command', 'args', 'status', 'started_at', 'finished_at',
        'duration_ms', 'duration_display_col', 'exit_code', 'triggered_by',
        'hostname', 'error_summary', 'stdout_pre', 'stderr_pre', 'meta',
    )
    fieldsets = (
        ('Buyruq', {'fields': ('command', 'args', 'triggered_by', 'hostname')}),
        ('Natija', {
            'fields': (
                'status', 'exit_code', 'started_at', 'finished_at',
                'duration_display_col', 'error_summary',
            ),
        }),
        ('Chiqish', {'fields': ('stdout_pre',)}),
        ('Xato oqimi', {'fields': ('stderr_pre',), 'classes': ('collapse',)}),
        ('Meta', {'fields': ('meta',), 'classes': ('collapse',)}),
    )
    date_hierarchy = 'started_at'
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @display(description='Holat')
    def status_badge(self, obj: CronRun) -> str:
        palette = {
            'success': ('#dcfce7', '#15803d', '\u2713 OK'),
            'failed':  ('#fee2e2', '#991b1b', '\u2716 XATO'),
            'running': ('#dbeafe', '#1e40af', '\u25cf ISHLAMOQDA'),
        }
        bg, fg, label = palette.get(obj.status, ('#f3f4f6', '#374151', obj.status))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:700">{}</span>',
            bg, fg, label,
        )

    @display(description='Ishga tushgan')
    def started_at_display(self, obj: CronRun) -> str:
        delta = timezone.now() - obj.started_at
        return format_html(
            '{} <span style="color:#999;font-size:11px">({} oldin)</span>',
            obj.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            _humanize_delta(delta),
        )

    @display(description='Davomiyligi')
    def duration_display_col(self, obj: CronRun) -> str:
        return obj.duration_display or ''

    @display(description='Manba')
    def triggered_by_display(self, obj: CronRun) -> str:
        icons = {'cron': '\u23f1', 'admin': '\U0001f464', 'manual': '\U0001f527'}
        icon = icons.get(obj.triggered_by, '\u00b7')
        return format_html('{} {}', icon, obj.triggered_by)

    @display(description='Xato')
    def error_preview(self, obj: CronRun) -> str:
        if not obj.error_summary:
            return ''
        return format_html(
            '<span style="color:#991b1b;font-family:monospace;font-size:11px">'
            '{}</span>', obj.error_summary[:80],
        )

    @display(description='Stdout')
    def stdout_pre(self, obj: CronRun) -> str:
        if not obj.stdout:
            return format_html('<em style="color:#999">(bo\u02bcsh)</em>')
        return format_html(
            '<pre style="background:#0f172a;color:#e2e8f0;padding:12px;'
            'border-radius:6px;max-height:400px;overflow:auto;'
            'font-size:12px;line-height:1.4">{}</pre>', obj.stdout,
        )

    @display(description='Stderr')
    def stderr_pre(self, obj: CronRun) -> str:
        if not obj.stderr:
            return format_html('<em style="color:#999">(bo\u02bcsh)</em>')
        return format_html(
            '<pre style="background:#450a0a;color:#fecaca;padding:12px;'
            'border-radius:6px;max-height:400px;overflow:auto;'
            'font-size:12px;line-height:1.4">{}</pre>', obj.stderr,
        )


def _humanize_delta(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    if total < 60:
        return f'{total}s'
    if total < 3600:
        return f'{total // 60}daq'
    if total < 86400:
        return f'{total // 3600}soat'
    return f'{total // 86400}kun'
