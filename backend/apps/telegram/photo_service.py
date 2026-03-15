"""Telegram profile photo download and caching service.

Rasm yuklash strategiyasi (tezlikdan sekinlikka):
  1. Cache: DB metadata + fayl tizimi (API chaqiruvsiz — tez)
  2. Bot API: getUserProfilePhotos (bot ko'rgan userlar uchun — xavfsiz)
  3. Telethon MTProto: download_profile_photo (Bot API ishlamasa — fallback)
  4. photo_url: TelegramEntity.photo_url (Login Widget avatar — oxirgi fallback)
  5. Negative cache: has_photo=False (1 kun TTL — takroriy so'rovlarni kamaytirish)

Bot API va Telethon farqi:
  - Bot API = xavfsiz, 30 req/sec, faqat bot bilan aloqa qilgan userlar uchun
  - Telethon = guruh/kanal/noma'lum userlar uchun, rate limited (15 req/min)
  - Ikkalasi ham TelegramRateLimiter orqali cheklanadi

Photo cache TelegramEntity modelida saqlanadi:
  - photo_file: fayl yo'li (MEDIA_ROOT ga nisbiy)
  - photo_url: to'liq URL (Nginx orqali serve qilinadi)
  - photo_fetched_at: qachon yuklangan
  - has_photo: None=noma'lum, True=bor, False=yo'q (negative cache)

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

# Ruxsat berilgan domenlar — boshqa domenlardan rasm yuklamaymiz (SSRF himoya)
ALLOWED_PHOTO_DOMAINS = {
    "t.me",
    "telegram.org",
    "cdn4.telegram-cdn.org",
    "cdn5.telegram-cdn.org",
    "jaysonkhan.com",
}

# Minimal rasm hajmi (bytes) — SVG, HTML, xato sahifalar ni filtrlash
MIN_PHOTO_SIZE = 500  # 500 bytes dan kichik rasm bo'lmaydi
# Image magic bytes for validation
IMAGE_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",      # JPEG
    b"\x89PNG": "image/png",             # PNG
    b"GIF8": "image/gif",               # GIF
    b"RIFF": "image/webp",              # WebP (RIFF header)
}


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


def _sanitize_entity_id(entity_id: str | int) -> str | None:
    """Validate and sanitize entity_id for safe filesystem use.

    Path traversal oldini olish: faqat raqam yoki raqam-prefiks qabul qiladi.
    Returns sanitized string or None if invalid.
    """
    entity_str = str(entity_id).strip()
    # Faqat raqamlar (manfiy bo'lishi mumkin — channel/supergroup)
    if not entity_str.lstrip("-").isdigit():
        logger.warning("Xavfsiz emas entity_id: %s", entity_str[:50])
        return None
    return entity_str


def _is_valid_image(data: bytes) -> bool:
    """Check if bytes represent a real image (not SVG, HTML, or error page).

    Magic bytes orqali tekshiradi — fayl kengaytmasiga ishonmaymiz.
    """
    if len(data) < MIN_PHOTO_SIZE:
        return False
    for magic in IMAGE_MAGIC_BYTES:
        if data[:len(magic)] == magic:
            return True
    return False


def _is_allowed_photo_url(url: str) -> bool:
    """Check if photo URL is from a trusted Telegram domain.

    SSRF oldini olish — faqat Telegram CDN domenlaridan yuklaymiz.
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Subdomen ham tekshiriladi (cdn1.telegram-cdn.org va h.k.)
        for allowed in ALLOWED_PHOTO_DOMAINS:
            if host == allowed or host.endswith(f".{allowed}"):
                return True
        logger.warning("Ruxsatsiz photo URL domeni: %s", host)
        return False
    except Exception:
        return False


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
            if resp.status_code == 200 and _is_valid_image(resp.content):
                logger.info(
                    "Photo Bot API orqali yuklandi: entity %s (%d bytes)",
                    entity_id, len(resp.content),
                )
                return resp.content

            if resp.status_code == 200:
                logger.warning(
                    "Bot API rasm emas (%s): %d bytes, magic=%s",
                    entity_id, len(resp.content), resp.content[:8].hex(),
                )
            else:
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

    Xavfsizlik:
      - Faqat Telegram domenlaridan ruxsat (SSRF oldini olish)
      - Yuklab olingan faylni image magic bytes orqali tekshiradi
      - SVG, HTML va boshqa noto'g'ri fayllarni filtrlaydi
    """
    if not photo_url:
        return None

    # ── SSRF himoya — faqat ishonchli domenlardan yuklaymiz ──
    if not _is_allowed_photo_url(photo_url):
        return None

    try:
        with httpx.Client(timeout=BOT_API_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(photo_url)
            if resp.status_code == 200 and _is_valid_image(resp.content):
                logger.info(
                    "Photo URL dan yuklandi: %s (%d bytes)",
                    photo_url[:80], len(resp.content),
                )
                return resp.content
            if resp.status_code == 200:
                logger.debug(
                    "Photo URL rasm emas (%s): %d bytes",
                    photo_url[:80], len(resp.content),
                )
    except Exception as e:
        logger.debug("Photo URL yuklashda xatolik (%s): %s", photo_url[:80], e)
    return None


# ── Telethon Fallback (Bot API ishlamasa) ─────────────────────────────────────


def _download_photo_via_telethon(entity_id: int) -> bytes | None:
    """Download profile photo via Telethon MTProto.

    Bot API faqat bot bilan aloqa qilgan userlar uchun ishlaydi.
    Guruh, kanal va boshqa userlar uchun Telethon kerak.

    Rate limited — mavjud TelegramRateLimiter orqali.
    Xatoliklar jimgina qaytariladi (None), log qilinadi.
    """
    try:
        from telegram.telegram_client import (
            get_rate_limiter,
            get_telegram_client,
            run_async,
        )

        limiter = get_rate_limiter()
        if not limiter.acquire(timeout=5):
            logger.debug("Telethon photo: rate limit, skip %s", entity_id)
            return None

        client = get_telegram_client()

        async def _fetch():
            return await client.download_profile_photo(entity_id, file=bytes)

        photo_bytes = run_async(_fetch())
        if photo_bytes and _is_valid_image(photo_bytes):
            logger.info(
                "Photo Telethon orqali yuklandi: entity %s (%d bytes)",
                entity_id, len(photo_bytes),
            )
            return photo_bytes
        return None
    except RuntimeError as e:
        logger.debug("Telethon client mavjud emas (%s): %s", entity_id, e)
        return None
    except Exception as e:
        logger.debug("Telethon photo download (%s): %s", entity_id, e)
        return None


# ── Main Public API ──────────────────────────────────────────────────────────


def get_entity_photo(
    entity_id: int | str,
    force_refresh: bool = False,
) -> tuple[bytes | None, str | None]:
    """Get profile photo for a Telegram entity (user/group/channel).

    Returns (photo_bytes, content_type) or (None, None).

    Strategy (tezlikdan sekinlikka):
      1. Cache: DB metadata + fayl tizimi (API chaqiruvsiz)
      2. Bot API: getUserProfilePhotos (bot ko'rgan userlar uchun)
      3. Telethon: download_profile_photo (guruh/kanal/noma'lum userlar uchun)
      4. photo_url: TelegramEntity.photo_url (Login Widget avatar)
      5. Negative cache: has_photo=False (1 kun TTL)
    """
    # 0. Sanitize entity_id (path traversal oldini olish)
    entity_str = _sanitize_entity_id(entity_id)
    if not entity_str:
        return None, None

    # 1. Check cache: TelegramEntity DB + filesystem
    if not force_refresh:
        try:
            entity_obj = TelegramEntity.objects.filter(
                telegram_id=int(entity_str),
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

    # 2. Validate entity_id (numeric)
    try:
        entity_int = int(entity_str)
    except (ValueError, TypeError):
        logger.warning("Noto'g'ri entity_id: %s", entity_id)
        return None, None

    # 3. Download via Bot API (xavfsiz, ban xavfi yo'q)
    photo_bytes = _download_photo_via_bot_api(entity_int)

    # 3.5 Fallback: Telethon (Bot API ishlamasa — guruh/kanal/noma'lum user uchun)
    if not photo_bytes:
        photo_bytes = _download_photo_via_telethon(entity_int)

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
    # Sanitize (path traversal himoya)
    safe_id = _sanitize_entity_id(entity_str)
    if not safe_id:
        return None, None

    # 1. DB-tracked cache
    try:
        entity_obj = TelegramEntity.objects.filter(
            telegram_id=int(safe_id),
            has_photo=True,
        ).first()
        if entity_obj and entity_obj.photo_file:
            abs_path = _photo_abs_path(safe_id)
            if abs_path.exists():
                return abs_path.read_bytes(), "image/jpeg"
    except (ValueError, TypeError):
        pass
    # 2. Bare filesystem cache (TelegramEntity yo'q)
    abs_path = _photo_abs_path(safe_id)
    if abs_path.exists():
        return abs_path.read_bytes(), "image/jpeg"
    return None, None
