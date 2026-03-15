"""Telegram profile photo download and caching service.

Universal xizmat — istalgan Telegram entity (user, group, channel, bot)
rasmini ID orqali oladi. 3 qatlam kesh: DB metadata + fayl tizimi + browser.

Photo cache TelegramEntity modelida saqlanadi:
  - photo_file: fayl yo'li (MEDIA_ROOT ga nisbiy)
  - photo_url: to'liq URL (https://jaysonkhan.com/media/osint/photos/123.jpg)
  - photo_fetched_at: qachon yuklangan
  - has_photo: None=noma'lum, True=bor, False=yo'q (negative cache)

Rasm yuklanganda photo_url avtomatik yangilanadi — har qanday joyda
(admin, template, API) shu URL orqali rasmni ko'rsatish mumkin.

Entity resolution strategy:
  1. Numeric ID orqali (tez, session cache da bo'lsa ishlaydi)
  2. Username orqali (OSINT cache dan, Telegram API call kerak)
  3. Hech biri ishlamasa → negative cache

Usage:
    from telegram.photo_service import get_entity_photo

    photo_bytes, content_type = get_entity_photo(123456789)
    # Returns (bytes, "image/jpeg") or (None, None)
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from telegram.models import TelegramEntity

logger = logging.getLogger(__name__)

PHOTO_DIR = "osint/photos"  # relative to MEDIA_ROOT
DEFAULT_DOMAIN = "https://jaysonkhan.com"
RATE_LIMIT_ACQUIRE_TIMEOUT = 10  # seconds to wait for rate limiter slot


def _get_site_domain() -> str:
    """Get site domain for constructing full photo URLs."""
    return getattr(settings, "TELEGRAM_WEBHOOK_DOMAIN", DEFAULT_DOMAIN)


def _photo_rel_path(entity_id: str | int) -> str:
    """Relative path under MEDIA_ROOT for a given entity."""
    return f"{PHOTO_DIR}/{entity_id}.jpg"


def _photo_abs_path(entity_id: str | int) -> Path:
    """Absolute filesystem path for a cached photo."""
    return Path(settings.MEDIA_ROOT) / _photo_rel_path(entity_id)


def _photo_full_url(entity_id: str | int) -> str:
    """Full public URL for a cached photo (served by Nginx).

    Example: https://jaysonkhan.com/media/osint/photos/123456.jpg
    """
    domain = _get_site_domain().rstrip("/")
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    rel_path = _photo_rel_path(entity_id)
    return f"{domain}{media_url}{rel_path}"


def _ensure_photo_dir():
    """Create the photo cache directory if it doesn't exist."""
    photo_dir = Path(settings.MEDIA_ROOT) / PHOTO_DIR
    photo_dir.mkdir(parents=True, exist_ok=True)


def _lookup_username(entity_id: int) -> str | None:
    """Try to find a username for entity_id from OSINT cache data.

    Checks: TelegramEntity username, then OSINT cache (usernames, stats_full, basic_info).
    """
    # 1. Check TelegramEntity itself
    try:
        entity_obj = TelegramEntity.objects.filter(telegram_id=entity_id).first()
        if entity_obj and entity_obj.username:
            return entity_obj.username
    except Exception as e:
        logger.debug("TelegramEntity lookup failed for %s: %s", entity_id, e)

    # 2. Check OSINT cache for username history
    try:
        from botproxy.models import OsintCache

        entity_str = str(entity_id)

        # Usernames history (most recent)
        entry = OsintCache.get_cached("usernames", entity_str)
        if entry and isinstance(entry.data, list) and entry.data:
            username = entry.data[0].get("name", "")
            if username:
                logger.debug("Username from usernames cache: %s", username)
                return username

        # stats_full
        entry = OsintCache.get_cached("stats_full", entity_str)
        if entry and isinstance(entry.data, dict):
            username = entry.data.get("username", "")
            if username:
                return username

        # basic_info
        entry = OsintCache.get_cached("basic_info", entity_str)
        if entry and isinstance(entry.data, dict):
            username = entry.data.get("username", "")
            if username:
                return username
    except Exception as e:
        logger.debug("OsintCache username lookup failed for %s: %s", entity_id, e)

    return None


async def _download_photo(client, entity_id: int, username: str | None = None) -> bytes | None:
    """Download profile photo for an entity via Telethon.

    IMPORTANT: `client` must be passed in from the sync caller (Django thread).
    Don't call get_telegram_client() here — it uses Django ORM which doesn't
    work from the background asyncio event loop thread.

    Strategy:
      1. Try numeric ID (works if entity is in session cache)
      2. If ValueError, try username from OSINT data (requires API call)
      3. Return photo bytes or None

    Raises FloodWaitError if rate limited by Telegram.
    """
    from telethon.errors import FloodWaitError

    tg_entity = None

    # Strategy 1: Try by numeric ID (fast, works if entity in session cache)
    try:
        tg_entity = await client.get_entity(entity_id)
    except FloodWaitError:
        raise
    except ValueError:
        logger.info("Entity %s ID orqali topilmadi, username ishlatiladi", entity_id)
    except Exception as e:
        logger.warning("Entity %s ni olishda xatolik: %s", entity_id, e)

    # Strategy 2: Try by username (if available)
    if tg_entity is None and username:
        try:
            tg_entity = await client.get_entity(username)
            logger.info("Entity %s username '%s' orqali topildi", entity_id, username)
        except FloodWaitError:
            raise
        except Exception as e:
            logger.warning("Username '%s' orqali ham topilmadi: %s", username, e)

    if tg_entity is None:
        logger.warning("Entity %s hech qanday usul bilan topilmadi", entity_id)
        return None

    # Download photo
    try:
        photo_bytes = await client.download_profile_photo(tg_entity, file=bytes)
        return photo_bytes
    except FloodWaitError:
        raise
    except Exception as e:
        logger.exception("Rasm yuklashda xatolik (entity %s): %s", entity_id, e)
        return None


def get_entity_photo(
    entity_id: int | str,
    force_refresh: bool = False,
) -> tuple[bytes | None, str | None]:
    """Get profile photo for a Telegram entity.

    Returns (photo_bytes, content_type) or (None, None).

    1. Check cache (TelegramEntity photo fields + filesystem)
    2. If cache miss/stale, download via Telethon
    3. Save to filesystem and update TelegramEntity
    4. On FloodWait or error, return cached version or None

    Thread-safe. Rate-limited.
    """
    from telegram.telegram_client import get_rate_limiter, get_telegram_client, run_async

    entity_str = str(entity_id)

    # 1. Check cache: TelegramEntity DB + filesystem
    if not force_refresh:
        try:
            entity_obj = TelegramEntity.objects.filter(telegram_id=int(entity_id)).first()
            if entity_obj and not entity_obj.is_photo_stale:
                if entity_obj.has_photo is False:
                    return None, None  # Negative cache
                if entity_obj.has_photo and entity_obj.photo_file:
                    abs_path = _photo_abs_path(entity_str)
                    if abs_path.exists():
                        return abs_path.read_bytes(), "image/jpeg"
                    # File deleted but cache entry exists — fall through to re-download
            elif entity_obj is None:
                # TelegramEntity yo'q — disk keshni tekshirish
                abs_path = _photo_abs_path(entity_str)
                if abs_path.exists():
                    return abs_path.read_bytes(), "image/jpeg"
        except (ValueError, TypeError):
            pass

    # 2. Rate limit check
    limiter = get_rate_limiter()
    if not limiter.acquire(timeout=RATE_LIMIT_ACQUIRE_TIMEOUT):
        logger.warning("Rate limit oshdi, entity %s uchun eski keshdan foydalaniladi", entity_str)
        return _try_stale_cache(entity_str)

    # 3. Download via Telethon
    try:
        entity_int = int(entity_id)
    except (ValueError, TypeError):
        logger.warning("Noto'g'ri entity_id: %s", entity_id)
        return None, None

    # Look up username for fallback resolution (Django ORM — main thread safe)
    username = _lookup_username(entity_int)

    # Get Telethon client in sync context (Django ORM-safe for session loading)
    try:
        client = get_telegram_client()
    except RuntimeError as e:
        logger.error("Telegram client olishda xatolik: %s", e)
        return None, None

    try:
        photo_bytes = run_async(_download_photo(client, entity_int, username=username))
    except Exception as e:
        error_name = type(e).__name__
        if "FloodWait" in error_name:
            logger.warning(
                "FloodWait entity %s uchun, eski keshdan foydalaniladi", entity_str
            )
        else:
            logger.exception("Rasm yuklashda kutilmagan xatolik (%s)", entity_str)
        return _try_stale_cache(entity_str)

    # 4. Save to cache (only UPDATE existing entities — never create phantom records)
    if photo_bytes:
        _ensure_photo_dir()
        abs_path = _photo_abs_path(entity_str)
        abs_path.write_bytes(photo_bytes)

        rel_path = _photo_rel_path(entity_str)
        full_url = _photo_full_url(entity_str)
        updated = TelegramEntity.objects.filter(telegram_id=entity_int).update(
            photo_file=rel_path,
            photo_url=full_url,
            photo_fetched_at=timezone.now(),
            has_photo=True,
        )
        if updated:
            logger.info("Photo saved for entity %s → %s", entity_str, full_url)
        else:
            logger.debug("Photo downloaded for %s but no TelegramEntity exists — skipped DB update", entity_str)
        return photo_bytes, "image/jpeg"

    # No photo — negative cache (only update existing entities)
    # NOTE: photo_url ni tozalamaymiz — u Telegram Login Widget dan kelgan
    # external avatar URL bo'lishi mumkin, photo_service boshqarmaydi.
    TelegramEntity.objects.filter(telegram_id=entity_int).update(
        has_photo=False,
        photo_fetched_at=timezone.now(),
    )
    return None, None


def _try_stale_cache(entity_str: str) -> tuple[bytes | None, str | None]:
    """Attempt to return a stale cached photo as fallback (circuit breaker).

    Checks both DB-tracked cache and bare filesystem cache (for entities
    that may not have a TelegramEntity record).
    """
    # 1. DB-tracked cache
    try:
        entity_obj = TelegramEntity.objects.filter(
            telegram_id=int(entity_str),
            has_photo=True,
        ).first()
        if entity_obj and entity_obj.photo_file:
            abs_path = _photo_abs_path(entity_str)
            if abs_path.exists():
                return abs_path.read_bytes(), "image/jpeg"
    except (ValueError, TelegramEntity.DoesNotExist):
        pass
    # 2. Bare filesystem cache (TelegramEntity yo'q)
    abs_path = _photo_abs_path(entity_str)
    if abs_path.exists():
        return abs_path.read_bytes(), "image/jpeg"
    return None, None
