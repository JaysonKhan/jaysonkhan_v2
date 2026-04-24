"""
Ops models — cron execution history + managed cron registry.

Every invocation of `python manage.py cron_run <target>` creates a
`CronRun` row. This gives the admin one place to see:
  - what ran, when, how long it took
  - exit status + stdout/stderr tail
  - who/what triggered it (cron vs. admin "Run now")

`ManagedCron` is a thin catalog of recognised commands — it stores the
schedule string + human name so the admin sees the full cron inventory
even before a command has ever fired. Rows auto-create when a CronRun
lands with a new command name.
"""
from __future__ import annotations

from django.db import models


class CronStatus(models.TextChoices):
    RUNNING = 'running', 'Ishlamoqda'
    SUCCESS = 'success', 'Muvaffaqiyatli'
    FAILED = 'failed', 'Xatolik'


class ManagedCron(models.Model):
    """Catalog of known scheduled commands."""

    command = models.CharField(
        max_length=120, unique=True, db_index=True,
        help_text='Django management command nomi.',
    )
    verbose_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    schedule = models.CharField(
        max_length=80, blank=True,
        help_text='Cron format: "*/10 * * * *". Faqat axborot — server crontab source of truth.',
    )
    enabled = models.BooleanField(default=True)
    category = models.CharField(max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cron jadval'
        verbose_name_plural = 'Cron jadvallar'
        ordering = ('category', 'command')

    def __str__(self):
        return self.verbose_name or self.command


class CronRun(models.Model):
    """One execution of a management command via the `cron_run` wrapper."""

    command = models.CharField(max_length=120, db_index=True)
    args = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16, choices=CronStatus.choices,
        default=CronStatus.RUNNING, db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    error_summary = models.CharField(max_length=300, blank=True)
    triggered_by = models.CharField(max_length=20, default='cron', db_index=True)
    hostname = models.CharField(max_length=80, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Cron yurishi'
        verbose_name_plural = 'Cron yurishlari'
        ordering = ('-started_at',)
        indexes = [
            models.Index(fields=['command', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self):
        return f'{self.command} @ {self.started_at:%Y-%m-%d %H:%M:%S}'

    @property
    def duration_display(self) -> str:
        if self.duration_ms is None:
            return ''
        if self.duration_ms < 1000:
            return f'{self.duration_ms}ms'
        if self.duration_ms < 60_000:
            return f'{self.duration_ms / 1000:.1f}s'
        return f'{self.duration_ms / 60_000:.1f}m'

    @property
    def is_running(self) -> bool:
        return self.status == CronStatus.RUNNING
