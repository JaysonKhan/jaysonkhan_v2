"""Telegram profile photo download and caching service.

Bot API yondashuv — xavfsiz, ban xavfi yo'q.
Telethon (MTProto) ISHLATILMAYDI — akkaunt ban bo'lish xavfi tufayli.

Photo cache TelegramEntity modelida saqlanadi:
  - photo_file: fayl yo'li (MEDIA_ROOT ga nisbiy)
  - photo_url: to'liq URL (https://jaysonkhan.com/media/osint/photos/123.jpg)
  - photo_fetched_at: qachon yuklangan
  - has_photo: None=noma'lum, True=bor, False=yo'q (negative cache)

Photo resolution strategy:
  1. Cache: DB metadata + fayl tizimi (tez)
  2. Bot API: getUserProfilePhotos (bot ko'rgan userlar uchun)
  3. photo_url fallback: TelegramEntity.photo_url (Login Widget avatar)
  4. Negative cache: 1 kun (qayta urinish tez)

Nima uchun Telethon emas?
  - Telethon = user account API (MTProto) → contacts.ResolveUsername rate limit
  - Ko'p chaqirsa → akkaunt ban/muzlatiladi
  - Bot API = rasmiy, xavfsiz, 30 req/sec limit
  - getUserProfilePhotos faqat bot bilan aloqa qilgan userlar uchun ishlaydi
  - Qolganlar uchun photo_url fallback (Login Widget avatar URL)

Usage:
    from telegram.photo_service import get_entity_photo

    photo_bytes, content_type = get_entity_photo(123456789)
    # Returns (bytes, "image/jpeg") or (None, None)
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from django.conf import settings
from django.utils import timezone

from telegram.models import TelegramEntity

logger = logging.getLogger(__name__)

PHOTO_DIR = "osint/photos"  # relative to MEDIA_ROOT
DEFAULT_DOMAIN = "https://jaysonkhan.com"
BOT_API_TIMEOUT = 15  # seconds for Bot API HTTP calls


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


# ── Bot API Photo Download ──────────────────────────────────────────────────


def _download_photo_via_bot_api(entity_id: int) -> bytes | None:
    """Download profile photo via Telegram Bot API.

    Xavfsiz yondashuv — ban xavfi yo'q.
    Faqat bot bilan aloqa qilgan (start bosgan, gruppada ko'rgan) userlar
    uchun ishlaydi. Qolganlar uchun None qaytaradi.

    Flow:
      1. getUserProfilePhotos → file_id olish
      2. getFile → file_path olish
      3. Download → bytes
    """
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN sozlanmagan — photo download imkonsiz")
        return None

    base_url = f"https://api.telegram.org/bot{bot_token}"

    try:
        with httpx.Client(timeout=BOT_API_TIMEOUT) as client:
            # 1. Get user profile photos (limit=1 — faqat birinchi rasm)
            resp = client.get(
                f"{base_url}/getUserProfilePhotos",
                params={"user_id": entity_id, "limit": 1},
            )
            data = resp.json()

            if not data.get("ok"):
                error_desc = data.get("description", "")
                # "Bad Request: user not found" — user bot bilan aloqa qilmagan
                if "not found" in error_desc.lower():
                    logger.debug(
                        "Entity %s bot bilan aloqa qilmagan: %s",
                        entity_id, error_desc,
                    )
                else:
                    logger.warning(
                        "getUserProfilePhotos xatolik (%s): %s",
                        entity_id, error_desc,
                    )
                return None

            photos = data.get("result", {}).get("photos", [])
            if not photos or not photos[0]:
                logger.debug("Entity %s ning rasmi yo'q (Bot API)", entity_id)
                return None

            # Eng katta versiyani olish (oxirgi element)
            largest = photos[0][-1]
            file_id = largest["file_id"]

            # 2. Get file path
            resp = client.get(
                f"{base_url}/getFile",
                params={"file_id": file_id},
            )
            file_data = resp.json()

            if not file_data.get("ok"):
                logger.warning(
                    "getFile xatolik (%s): %s",
                    entity_id, file_data.get("description", ""),
                )
                return None

            file_path = file_data["result"]["file_path"]

            # 3. Download the actual photo file
            resp = client.get(
                f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            )
            if resp.status_code == 200 and len(resp.content) > 100:
                logger.info(
                    "Photo Bot API orqali yuklandi: entity %s (%d bytes)",
                    entity_id, len(resp.content),
                )
                return resp.content

            logger.warning(
                "Photo download xatolik (%s): HTTP %s",
                entity_id, resp.status_code,
            )
            return None

    except httpx.TimeoutException:
        logger.warning("Bot API timeout: entity %s", entity_id)
        return None
    except Exception as e:
        logger.warning("Bot API xatolik (%s): %s", entity_id, e)
        return None


def _download_photo_from_url(photo_url: str) -> bytes | None:
    """Download photo from an external URL (e.g. Telegram Login Widget avatar).

    Fallback sifatida ishlatiladi — Bot API user ni topolmaganda,
    TelegramEntity.photo_url dan rasmni yuklab oladi.
    """
    if not photo_url:
        return None
    try:
        with httpx.Client(timeout=BOT_API_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(photo_url)
            if resp.status_code == 200 and len(resp.content) > 100:
                logger.info(
                    "Photo URL dan yuklandi: %s (%d bytes)",
                    photo_url[:80], len(resp.content),
                )
                return resp.content
    except Exception as e:
        logger.debug("Photo URL yuklashda xatolik (%s): %s", photo_url[:80], e)
    return None


# ── Main Public API ──────────────────────────────────────────────────────────


def get_entity_photo(
    entity_id: int | str,
    force_refresh: bool = False,
) -> tuple[bytes | None, str | None]:
    """Get profile photo for a Telegram entity.

    Returns (photo_bytes, content_type) or (None, None).

    Strategy (xavfsiz — Telethon/MTProto ISHLATILMAYDI):
      1. Cache: DB metadata + fayl tizimi (tez)
      2. Bot API: getUserProfilePhotos (xavfsiz, ban xavfi yo'q)
      3. photo_url fallback: TelegramEntity.photo_url (Login Widget avatar)
      4. Negative cache: has_photo=False (1 kun TTL)
    """
    entity_str = str(entity_id)

    # 1. Check cache: TelegramEntity DB + filesystem
    if not force_refresh:
        try:
            entity_obj = TelegramEntity.objects.filter(
                telegram_id=int(entity_id),
            ).first()
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

    # 2. Validate entity_id
    try:
        entity_int = int(entity_id)
    except (ValueError, TypeError):
        logger.warning("Noto'g'ri entity_id: %s", entity_id)
        return None, None

    # 3. Download via Bot API (xavfsiz, ban xavfi yo'q)
    photo_bytes = _download_photo_via_bot_api(entity_int)

    # 4. Fallback: download from entity's external photo_url
    if not photo_bytes:
        try:
            entity_obj = TelegramEntity.objects.filter(
                telegram_id=entity_int,
            ).only("photo_url").first()
            if entity_obj and entity_obj.photo_url:
                photo_bytes = _download_photo_from_url(entity_obj.photo_url)
        except Exception:
            pass

    # 5. Save to cache (only UPDATE existing entities — never create phantom records)
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
            logger.info("Photo saqlandi: entity %s → %s", entity_str, full_url)
        else:
            logger.debug(
                "Photo yuklandi (%s) lekin TelegramEntity yo'q — DB skip",
                entity_str,
            )
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
