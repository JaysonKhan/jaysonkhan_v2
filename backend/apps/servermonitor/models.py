"""
Servermonitor models — service health history.

Every run of ``service_health_check`` (cron, ~ every 5 min) creates one
``ServiceCheckResult`` row per monitored unit. The rows give:

  - History of when each service was up/down
  - Trigger for state-change Telegram alerts (only flips alert)
  - Restart counter for daily report ("nginx restarted 3x today")

Retention: kept indefinitely for now. ~12 services × 12 checks/hour × 24
× 90 days ≈ 310k rows — fits comfortably. A cleanup task can be added
later if needed.
"""
from __future__ import annotations

from django.db import models


class ServiceCheckResult(models.Model):
    """One systemd service status sample taken by ``service_health_check``."""

    service_unit = models.CharField(
        max_length=80, db_index=True,
        help_text='Systemd unit name, e.g. "uzexam-bot" or "postgresql@16-main".',
    )
    service_group = models.CharField(
        max_length=20, db_index=True, blank=True,
        help_text='apps / infra / mail / security',
    )
    service_display = models.CharField(
        max_length=120, blank=True,
        help_text='Human-readable name shown in alerts.',
    )

    is_active = models.BooleanField(db_index=True)
    status_text = models.CharField(
        max_length=40,
        help_text='Raw `systemctl is-active` output: active / inactive / failed / activating.',
    )
    memory_mb = models.FloatField(null=True, blank=True)
    uptime_text = models.CharField(max_length=120, blank=True)

    # ── State-change tracking ──
    is_state_change = models.BooleanField(
        default=False, db_index=True,
        help_text='True when this row differs from the previous check.',
    )
    previous_active = models.BooleanField(
        null=True, blank=True,
        help_text='Active state of the previous check, if any.',
    )
    alert_sent = models.BooleanField(
        default=False, db_index=True,
        help_text='Telegram alert was dispatched (only critical services).',
    )

    checked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Servis tekshiruvi'
        verbose_name_plural = 'Servis tekshiruvlari'
        ordering = ('-checked_at',)
        indexes = [
            models.Index(fields=['service_unit', '-checked_at']),
            models.Index(fields=['is_state_change', '-checked_at']),
            models.Index(fields=['service_group', '-checked_at']),
        ]

    def __str__(self) -> str:
        flag = '✓' if self.is_active else '✗'
        return f'{flag} {self.service_unit} @ {self.checked_at:%Y-%m-%d %H:%M:%S}'

    @property
    def transition_label(self) -> str:
        """Human-readable transition for display."""
        if not self.is_state_change:
            return ''
        prev = 'active' if self.previous_active else 'inactive'
        new = 'active' if self.is_active else 'inactive'
        return f'{prev} → {new}'
