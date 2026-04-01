"""Unified Telegram entity models.

Barcha Telegram foydalanuvchilari, guruhlar, kanallar va botlar uchun
yagona model. Har bir entity qaysi servisdan (site, OSINT, talabaovozi)
topilganligini EntitySource orqali kuzatadi.

TelegramSession — Telethon StringSession ni PostgreSQL da saqlaydi
(Gunicorn multi-worker muhitida xavfsiz).
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, models
from django.utils import timezone


# ── TelegramEntity ───────────────────────────────────────────────────────────


class TelegramEntity(models.Model):
    """Universal Telegram entity: user, bot, group, supergroup, channel.

    Barcha servislar (site login, OSINT, talabaovozi bot) shu model
    orqali ishlaydi. Har bir entity ning qaysi servisdan topilganligini
    EntitySource modeli kuzatadi.

    Photo cache: photo_file (filesystem path), photo_fetched_at, has_photo
    — alohida OsintPhotoCache modeli o'rniga shu yerda saqlanadi.
    """

    class EntityType(models.TextChoices):
        USER = "user", "User"
        BOT = "bot", "Bot"
        GROUP = "group", "Group"
        SUPERGROUP = "supergroup", "Supergroup"
        CHANNEL = "channel", "Channel"

    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    entity_type = models.CharField(
        max_length=20,
        choices=EntityType.choices,
        default=EntityType.USER,
    )

    # ── Identity ─────────────────────────────────────────────────────────────
    first_name = models.CharField(max_length=255, blank=True, default="")
    last_name = models.CharField(max_length=255, blank=True, default="")
    username = models.CharField(
        max_length=255, blank=True, default="", db_index=True,
    )
    title = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Group/channel title",
    )
    phone = models.CharField(max_length=30, blank=True, default="")
    bio = models.TextField(blank=True, default="")

    # ── Photo cache (OsintPhotoCache ni almashtiradi) ────────────────────────
    photo_file = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Relative path under MEDIA_ROOT (e.g. osint/photos/123.jpg)",
    )
    photo_fetched_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Qachon Telegram dan yuklangan",
    )
    has_photo = models.BooleanField(
        null=True, default=None,
        help_text="None=unknown, True=has photo, False=no photo (negative cache)",
    )

    # ── Photo URL (universal — Login Widget yoki photo_service dan) ──────────
    photo_url = models.URLField(
        blank=True, default="",
        help_text="Public avatar URL — photo service yuklaganda avtomatik yangilanadi",
    )
    auth_date = models.IntegerField(
        null=True, blank=True,
        help_text="Unix timestamp from Telegram Login Widget",
    )

    # ── Telegram metadata (OSINT yoki direct API dan) ────────────────────────
    is_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    is_scam = models.BooleanField(default=False)
    is_fake = models.BooleanField(default=False)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram Entity"
        verbose_name_plural = "Telegram Entities"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.display_name

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        if self.entity_type in (
            self.EntityType.GROUP,
            self.EntityType.SUPERGROUP,
            self.EntityType.CHANNEL,
        ):
            return self.title or f"Entity #{self.telegram_id}"
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.username or f"User #{self.telegram_id}"

    @property
    def display_name(self) -> str:
        return self.full_name

    @property
    def is_photo_stale(self) -> bool:
        """Photo keshi eskirganmi.

        Positive cache (has_photo=True): 7 kun (OSINT_PHOTO_CACHE_DAYS).
        Negative cache (has_photo=False): 1 kun — tezroq qayta urinish.
        """
        if not self.photo_fetched_at:
            return True
        if self.has_photo is False:
            # Negative cache — tezroq expire bo'lsin
            neg_ttl = getattr(settings, "OSINT_PHOTO_NEG_CACHE_DAYS", 1)
            return timezone.now() - self.photo_fetched_at > timedelta(days=neg_ttl)
        ttl = getattr(settings, "OSINT_PHOTO_CACHE_DAYS", 7)
        return timezone.now() - self.photo_fetched_at > timedelta(days=ttl)

    @property
    def photo_abs_path(self) -> str:
        """Absolute filesystem path to cached photo."""
        if not self.photo_file:
            return ""
        return str(Path(settings.MEDIA_ROOT) / self.photo_file)

    def get_photo_url(self) -> str:
        """Best available photo URL (photo_url > empty string)."""
        return self.photo_url or ""

    # ── Class methods ────────────────────────────────────────────────────────

    @classmethod
    def get_or_create_from_telegram(cls, data: dict) -> TelegramEntity:
        """Create or update entity from Telegram Login Widget / API data.

        Universal factory — Login Widget, OSINT, bot API dan foydalanadi.

        MUHIM: Faqat bo'sh bo'lmagan qiymatlar bilan yangilaydi — mavjud
        ma'lumotlar (masalan, OSINT dan olingan phone, bio) ustiga bo'sh
        qiymat yozilmaydi.

        Args:
            data: dict with keys: id, first_name, last_name, username,
                  photo_url, auth_date (all optional except id)
        """
        telegram_id = int(data["id"])
        defaults = {}

        # Faqat bo'sh bo'lmagan qiymatlarni qo'shish — mavjud datani
        # yo'qotmaslik uchun (masalan, OSINT dan phone/bio bor,
        # Login Widget da yo'q — ustiga yozilmasligi kerak)
        for field in ("first_name", "last_name", "username"):
            if data.get(field):
                defaults[field] = data[field]

        if data.get("photo_url"):
            defaults["photo_url"] = data["photo_url"]
        if "auth_date" in data:
            defaults["auth_date"] = int(data["auth_date"])

        entity, created = cls.objects.update_or_create(
            telegram_id=telegram_id,
            defaults=defaults,
        )
        return entity

    @classmethod
    def get_or_create_with_source(
        cls, data: dict, service: str = "site",
    ) -> TelegramEntity:
        """Create/update entity and register its service source.

        Combines get_or_create_from_telegram + EntitySource creation.
        Used by all Telegram login views to avoid code duplication.

        Args:
            data: Telegram user data dict (id, first_name, etc.)
            service: EntitySource.Service value (default: 'site')
        """
        entity = cls.get_or_create_from_telegram(data)
        # Lazy import to avoid circular ref at class definition time
        EntitySource.objects.get_or_create(entity=entity, service=service)
        return entity


# ── EntitySource ─────────────────────────────────────────────────────────────


class EntitySource(models.Model):
    """Tracks which service(s) discovered/interact with a TelegramEntity.

    Bitta entity bir nechta servisda bo'lishi mumkin (masalan, OSINT
    qidiruvda topilgan va saytga ham kirgan). Har bir servis uchun
    alohida yozuv — role va extra_data bilan.
    """

    class Service(models.TextChoices):
        SITE = "site", "Website (jaysonkhan.com)"
        OSINT = "osint", "OSINT"
        TALABAOVOZI = "talabaovozi", "TalabaOvozi"

    entity = models.ForeignKey(
        TelegramEntity,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    service = models.CharField(
        max_length=20,
        choices=Service.choices,
    )
    role = models.CharField(
        max_length=50, blank=True, default="",
        help_text="e.g. member, admin, subscriber, searched",
    )
    extra_data = models.JSONField(
        default=dict, blank=True,
        help_text="Service-specific metadata",
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("entity", "service")
        verbose_name = "Entity Source"
        verbose_name_plural = "Entity Sources"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.entity.display_name} — {self.get_service_display()}"


# ── TelegramSession ─────────────────────────────────────────────────────────


class TelegramSession(models.Model):
    """Stores Telethon session + API config in PostgreSQL.

    SQLite file-based session Gunicorn multi-worker muhitida ishlamaydi
    (database is locked / readonly database xatolari). Buning o'rniga
    session string sifatida PostgreSQL da saqlanadi.

    API credentials (api_id, api_hash) ham shu yerda saqlanadi —
    admin paneldan boshqarish mumkin (.env ni o'zgartirmasdan).

    Singleton — faqat bitta yozuv (pk=1).
    """

    # ── API Credentials ──────────────────────────────────────────────────────
    api_id = models.IntegerField(
        null=True, blank=True,
        help_text="Telegram API ID (my.telegram.org/apps dan oling)",
    )
    api_hash = models.CharField(
        max_length=64, blank=True, default="",
        help_text="Telegram API Hash",
    )

    # ── Session Data ─────────────────────────────────────────────────────────
    session_string = models.TextField(
        blank=True, default="",
        help_text="Telethon StringSession.save() natijasi",
    )
    account_id = models.BigIntegerField(
        null=True, blank=True,
        help_text="Telegram account ID (me.id)",
    )
    account_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Account display name (first_name + username)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram Session"
        verbose_name_plural = "Telegram Sessions"

    def __str__(self):
        if self.account_name:
            return f"Session: {self.account_name} (ID: {self.account_id})"
        return f"Session #{self.pk}"

    @classmethod
    def get_session_string(cls) -> str | None:
        """Get stored session string, or None if not set."""
        try:
            obj = cls.objects.first()
            return obj.session_string if obj else None
        except DatabaseError:
            return None

    @classmethod
    def save_session(
        cls,
        session_string: str,
        account_id: int | None = None,
        account_name: str = "",
    ):
        """Save or update session string (singleton — always pk=1).

        Atomic via update_or_create — safe for Gunicorn multi-worker.
        """
        cls.objects.update_or_create(
            pk=1,
            defaults={
                "session_string": session_string,
                "account_id": account_id,
                "account_name": account_name,
            },
        )

    @classmethod
    def clear_session(cls):
        """Delete all session records."""
        cls.objects.all().delete()

    # ── API Config ───────────────────────────────────────────────────────────

    @classmethod
    def get_api_config(cls) -> tuple[int, str] | None:
        """Get API credentials from DB.

        Returns (api_id, api_hash) or None if not configured.
        """
        try:
            obj = cls.objects.first()
            if obj and obj.api_id and obj.api_hash:
                return obj.api_id, obj.api_hash
        except DatabaseError:
            pass
        return None

    @classmethod
    def save_api_config(cls, api_id: int, api_hash: str):
        """Save API credentials (singleton — always pk=1).

        session_string ni o'zgartirmaydi — faqat API config ni yangilaydi.
        """
        obj = cls.objects.first()
        if obj:
            obj.api_id = api_id
            obj.api_hash = api_hash
            obj.save(update_fields=["api_id", "api_hash", "updated_at"])
        else:
            cls.objects.create(
                pk=1,
                api_id=api_id,
                api_hash=api_hash,
            )
