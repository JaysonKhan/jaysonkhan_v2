"""Cache models for FunStat OSINT data.

First models.py for botproxy — previously modelless.
Run: python manage.py makemigrations botproxy && python manage.py migrate
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


class OsintCache(models.Model):
    """Generic cache for FunStat API responses.

    Cache key = (endpoint_type, target_id, page).
    """

    ENDPOINT_CHOICES = [
        # Free
        ("stats_min", "Basic Stats (free)"),
        ("groups_count", "Groups Count (free)"),
        ("messages_count", "Messages Count (free)"),
        ("reputation", "Reputation (free)"),
        # Paid — User
        ("stats_full", "Full Stats (1)"),
        ("groups", "Groups (5)"),
        ("names", "Name History (3)"),
        ("usernames", "Username History (3)"),
        ("stickers", "Stickers (1)"),
        ("gifts", "Gift Relations (5)"),
        ("common_groups_stat", "Common Groups Stat (5)"),
        ("messages", "Messages (10)"),
        # Search / resolve
        ("basic_info", "Basic Info (0.10)"),
        ("resolve_username", "Resolve Username (0.10)"),
        ("username_usage", "Username Usage (0.1)"),
        # Groups
        ("group_info", "Group Info (0.01)"),
        ("group_members", "Group Members (15)"),
        ("common_groups", "Common Groups (0.5)"),
        # Text
        ("text_search", "Text Search (0.1)"),
    ]

    endpoint_type = models.CharField(max_length=30, choices=ENDPOINT_CHOICES, db_index=True)
    target_id = models.CharField(
        max_length=255, db_index=True,
        help_text="Telegram user/group ID, username, or search query",
    )
    page = models.PositiveIntegerField(default=1, help_text="Page for paginated endpoints")

    data = models.JSONField(help_text="The 'data' payload from FunStat response")
    tech = models.JSONField(
        default=dict, blank=True,
        help_text="The 'tech' metadata (request_cost, current_ballance, duration)",
    )

    fetched_at = models.DateTimeField(default=timezone.now)
    fetched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    class Meta:
        unique_together = ("endpoint_type", "target_id", "page")
        ordering = ["-fetched_at"]
        verbose_name = "OSINT Cache Entry"
        verbose_name_plural = "OSINT Cache Entries"

    def __str__(self):
        return f"{self.endpoint_type}:{self.target_id} (p{self.page})"

    @property
    def is_stale(self) -> bool:
        ttl = getattr(settings, "FUNSTAT_CACHE_TTL_HOURS", 24)
        return timezone.now() - self.fetched_at > timedelta(hours=ttl)

    @classmethod
    def get_cached(cls, endpoint_type: str, target_id: str | int, page: int = 1):
        """Return cached entry or None."""
        try:
            return cls.objects.get(
                endpoint_type=endpoint_type,
                target_id=str(target_id),
                page=page,
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def set_cache(
        cls, endpoint_type: str, target_id: str | int, data,
        tech: dict | None = None, page: int = 1, user=None,
    ):
        """Create or update cache entry."""
        obj, _ = cls.objects.update_or_create(
            endpoint_type=endpoint_type,
            target_id=str(target_id),
            page=page,
            defaults={
                "data": data,
                "tech": tech or {},
                "fetched_at": timezone.now(),
                "fetched_by": user,
            },
        )
        return obj


class OsintSearchLog(models.Model):
    """Audit log of OSINT searches performed."""

    QUERY_TYPE_CHOICES = [
        ("id", "User ID"),
        ("username", "Username"),
        ("text", "Text Search"),
    ]

    query = models.CharField(max_length=255)
    query_type = models.CharField(max_length=20, choices=QUERY_TYPE_CHOICES)
    resolved_id = models.BigIntegerField(null=True, blank=True)
    searched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    searched_at = models.DateTimeField(default=timezone.now)
    api_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-searched_at"]

    def __str__(self):
        return f"{self.query_type}:{self.query} at {self.searched_at}"


class OsintPhotoCache(models.Model):
    """Filesystem-backed cache metadata for Telegram profile photos.

    Photos are stored at MEDIA_ROOT/osint/photos/{entity_id}.jpg.
    This model tracks cache validity and negative results (entity has no photo).
    """

    entity_id = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="Telegram entity ID (user, group, channel, bot)",
    )
    has_photo = models.BooleanField(
        default=False,
        help_text="Whether this entity has a profile photo",
    )
    photo_path = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Relative path under MEDIA_ROOT",
    )
    fetched_at = models.DateTimeField(default=timezone.now)
    file_size = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "OSINT Photo Cache"
        verbose_name_plural = "OSINT Photo Cache"

    def __str__(self):
        status = "has_photo" if self.has_photo else "no_photo"
        return f"photo:{self.entity_id} ({status})"

    @property
    def is_stale(self) -> bool:
        ttl = getattr(settings, "OSINT_PHOTO_CACHE_DAYS", 7)
        return timezone.now() - self.fetched_at > timedelta(days=ttl)

    @property
    def full_path(self) -> str:
        """Absolute filesystem path to the cached photo."""
        if not self.photo_path:
            return ""
        return str(Path(settings.MEDIA_ROOT) / self.photo_path)

    @classmethod
    def get_cached(cls, entity_id: str | int):
        """Return cached entry if it exists and is not stale."""
        try:
            entry = cls.objects.get(entity_id=str(entity_id))
            if entry.is_stale:
                return None
            return entry
        except cls.DoesNotExist:
            return None

    @classmethod
    def set_cache(cls, entity_id: str | int, has_photo: bool,
                  photo_path: str = "", file_size: int = 0):
        """Create or update photo cache entry."""
        obj, _ = cls.objects.update_or_create(
            entity_id=str(entity_id),
            defaults={
                "has_photo": has_photo,
                "photo_path": photo_path,
                "file_size": file_size,
                "fetched_at": timezone.now(),
            },
        )
        return obj
