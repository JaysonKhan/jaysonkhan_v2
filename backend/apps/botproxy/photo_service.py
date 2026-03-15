"""Telegram profile photo download and caching service.

Universal xizmat — istalgan Telegram entity (user, group, channel, bot)
rasmini ID orqali oladi. 3 qatlam kesh: DB metadata + fayl tizimi + browser.

Usage:
    from botproxy.photo_service import get_entity_photo

    photo_bytes, content_type = get_entity_photo(123456789)
    # Returns (bytes, "image/jpeg") or (None, None)
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings

from botproxy.models import OsintPhotoCache

logger = logging.getLogger(__name__)

PHOTO_DIR = "osint/photos"  # relative to MEDIA_ROOT


def _photo_rel_path(entity_id: str | int) -> str:
    """Relative path under MEDIA_ROOT for a given entity."""
    return f"{PHOTO_DIR}/{entity_id}.jpg"


def _photo_abs_path(entity_id: str | int) -> Path:
    """Absolute filesystem path for a cached photo."""
    return Path(settings.MEDIA_ROOT) / _photo_rel_path(entity_id)


def _ensure_photo_dir():
    """Create the photo cache directory if it doesn't exist."""
    photo_dir = Path(settings.MEDIA_ROOT) / PHOTO_DIR
    photo_dir.mkdir(parents=True, exist_ok=True)


async def _download_photo(entity_id: int) -> bytes | None:
    """Download profile photo for an entity via Telethon.

    Returns photo bytes or None if no photo exists.
    Raises FloodWaitError if rate limited by Telegram.
    """
    from telethon.errors import FloodWaitError

    from botproxy.telegram_client import get_telegram_client

    client = get_telegram_client()

    try:
        entity = await client.get_entity(entity_id)
    except FloodWaitError:
        raise
    except ValueError:
        logger.warning("Entity %s Telegram da topilmadi", entity_id)
        return None
    except Exception as e:
        logger.exception("Entity %s ni olishda xatolik: %s", entity_id, e)
        return None

    try:
        photo_bytes = await client.download_profile_photo(entity, file=bytes)
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

    1. Check cache (OsintPhotoCache model + filesystem)
    2. If cache miss/stale, download via Telethon
    3. Save to filesystem and update cache model
    4. On FloodWait or error, return cached version or None

    Thread-safe. Rate-limited.
    """
    from botproxy.telegram_client import get_rate_limiter, run_async

    entity_str = str(entity_id)

    # 1. Check cache
    if not force_refresh:
        cached = OsintPhotoCache.get_cached(entity_str)
        if cached is not None:
            if not cached.has_photo:
                return None, None  # Negative cache
            abs_path = _photo_abs_path(entity_str)
            if abs_path.exists():
                return abs_path.read_bytes(), "image/jpeg"
            # File deleted but cache entry exists — fall through to re-download

    # 2. Rate limit check
    limiter = get_rate_limiter()
    if not limiter.acquire(timeout=10):
        logger.warning("Rate limit oshdi, entity %s uchun eski keshdan foydalaniladi", entity_str)
        return _try_stale_cache(entity_str)

    # 3. Download via Telethon
    try:
        entity_int = int(entity_id)
    except (ValueError, TypeError):
        logger.warning("Noto'g'ri entity_id: %s", entity_id)
        return None, None

    try:
        photo_bytes = run_async(_download_photo(entity_int))
    except Exception as e:
        error_name = type(e).__name__
        if "FloodWait" in error_name:
            logger.warning(
                "FloodWait entity %s uchun, eski keshdan foydalaniladi", entity_str
            )
        else:
            logger.exception("Rasm yuklashda kutilmagan xatolik (%s)", entity_str)
        return _try_stale_cache(entity_str)

    # 4. Save to cache
    if photo_bytes:
        _ensure_photo_dir()
        abs_path = _photo_abs_path(entity_str)
        abs_path.write_bytes(photo_bytes)
        OsintPhotoCache.set_cache(
            entity_id=entity_str,
            has_photo=True,
            photo_path=_photo_rel_path(entity_str),
            file_size=len(photo_bytes),
        )
        return photo_bytes, "image/jpeg"

    # No photo — negative cache
    OsintPhotoCache.set_cache(entity_id=entity_str, has_photo=False)
    return None, None


def _try_stale_cache(entity_str: str) -> tuple[bytes | None, str | None]:
    """Attempt to return a stale cached photo as fallback (circuit breaker)."""
    try:
        entry = OsintPhotoCache.objects.get(entity_id=entity_str)
        if entry.has_photo:
            abs_path = _photo_abs_path(entity_str)
            if abs_path.exists():
                return abs_path.read_bytes(), "image/jpeg"
    except OsintPhotoCache.DoesNotExist:
        pass
    return None, None
