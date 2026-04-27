"""
Admin surface for ServiceCheckResult.

Two main jobs:
  - History: filter by service, group, state-change → audit when a unit flapped
  - Live trigger: "Run service_health_check now" admin action so the operator
    can verify the alert pipeline without waiting for the cron tick.

Pattern mirrors apps/ops/admin.py (Unfold ModelAdmin + spawn cron_run via
detached subprocess).
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

from servermonitor.models import ServiceCheckResult


# ── Helpers (parallel to ops/admin.py) ────────────────────────────────────────


def _manage_py_path() -> Path:
    candidate = Path(settings.BASE_DIR) / 'manage.py'
    if candidate.exists():
        return candidate
    cwd = Path.cwd() / 'manage.py'
    if cwd.exists():
        return cwd
    return candidate


def _spawn_cron_run(target: str) -> None:
    """Start a detached subprocess so the admin response isn't blocked."""
    python = sys.executable
    manage_py = _manage_py_path()
    cmd = [python, str(manage_py), 'cron_run', target, '--triggered-by=admin']
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        cwd=str(manage_py.parent),
        env={**os.environ},
    )


# ── ServiceCheckResult admin ──────────────────────────────────────────────────


@admin.register(ServiceCheckResult)
class ServiceCheckResultAdmin(UnfoldAdmin):
    """Audit history of every service health probe."""

    list_display = (
        'service_pill',
        'group_pill',
        'status_pill',
        'mem_display',
        'transition_display',
        'alert_sent',
        'checked_at',
    )
    list_filter = (
        'service_unit',
        'service_group',
        'is_active',
        'is_state_change',
        'alert_sent',
    )
    search_fields = ('service_unit', 'service_display', 'status_text')
    readonly_fields = (
        'service_unit', 'service_group', 'service_display',
        'is_active', 'status_text', 'memory_mb', 'uptime_text',
        'is_state_change', 'previous_active', 'alert_sent',
        'checked_at',
    )
    date_hierarchy = 'checked_at'
    list_per_page = 50
    actions = ['action_run_health_check']

    # ── Custom display columns ──

    @display(description='Servis', ordering='service_unit')
    def service_pill(self, obj: ServiceCheckResult) -> str:
        label = obj.service_display or obj.service_unit
        return format_html(
            '<span title="{}"><b>{}</b><br><small style="color:#888">{}</small></span>',
            obj.service_unit, label, obj.service_unit,
        )

    @display(description='Guruh', ordering='service_group')
    def group_pill(self, obj: ServiceCheckResult) -> str:
        colors = {
            'apps':     '#6366f1',
            'infra':    '#0891b2',
            'mail':     '#a855f7',
            'security': '#dc2626',
        }
        c = colors.get(obj.service_group, '#64748b')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:6px;font-size:11px;">{}</span>',
            c, obj.service_group or '—',
        )

    @display(description='Holat', ordering='is_active')
    def status_pill(self, obj: ServiceCheckResult) -> str:
        if obj.is_active:
            return format_html(
                '<span style="color:#16a34a;font-weight:600;">● {}</span>',
                obj.status_text,
            )
        return format_html(
            '<span style="color:#dc2626;font-weight:600;">● {}</span>',
            obj.status_text,
        )

    @display(description='Xotira')
    def mem_display(self, obj: ServiceCheckResult) -> str:
        if obj.memory_mb is None:
            return '—'
        return f'{obj.memory_mb} MB'

    @display(description="O'zgarish", ordering='is_state_change')
    def transition_display(self, obj: ServiceCheckResult) -> str:
        if not obj.is_state_change:
            return ''
        prev = '🟢' if obj.previous_active else '🔴'
        new = '🟢' if obj.is_active else '🔴'
        return format_html('{} → {} <small>{}</small>', prev, new, obj.transition_label)

    # ── Actions ──

    @action(description='Hozir tekshirish (service_health_check)')
    def action_run_health_check(self, request, queryset):
        _spawn_cron_run('service_health_check')
        self.message_user(
            request,
            'service_health_check fonda ishga tushirildi — natijalar bir necha sekundda paydo boʼladi.',
            level=messages.INFO,
        )

    # ── Permissions: read-only via UI; writes happen via the cron command ──

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow superuser to prune old rows manually if needed.
        return request.user.is_superuser


# ── Custom changelist link: "Run health check now" ──
# Enabled on the changelist toolbar via Unfold's actions=[].
