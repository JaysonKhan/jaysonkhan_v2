"""Telethon-based MTProto service for channel/group OSINT operations.

Kanal va guruhlar haqida ma'lumot olish uchun xavfsiz Telethon wrapper.
Barcha chaqiruvlar rate limiter orqali o'tadi (ban oldini olish).
Django sync views uchun run_async() ishlatadi.

Operatsiyalar:
  - get_entity_profile: kanal/guruh profil ma'lumotlari
  - get_channel_messages: xabarlar ro'yxati (paginatsiya bilan)
  - search_channel_messages: xabar qidirish

Xavfsizlik:
  - Rate limit: 15 req/min (mavjud TelegramRateLimiter)
  - FloodWaitError: _handle_telethon_error() orqali boshqariladi
  - Xabar limiti: har so'rovda max 50 ta
  - A'zolar ro'yxati: QILMAYDI (eng xavfli operatsiya)

Usage:
    from telegram.mtproto_service import get_entity_profile, get_channel_messages

    result = get_entity_profile(channel_id)
    if result.error:
        print(result.error)
    else:
        print(result.data["title"])
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MTProtoResult:
    """Standardized result from MTProto operations."""

    data: Any = None
    error: str | None = None
    rate_limited: bool = False


# ── Entity Profile ──────────────────────────────────────────────────────────


def get_entity_profile(entity_id: int | str) -> MTProtoResult:
    """Get full profile info for a channel/group/supergroup via Telethon.

    GetFullChannelRequest (kanal/supergroup) yoki GetFullChatRequest (oddiy guruh)
    chaqiradi. Natija TelegramEntity ga saqlanadi.

    Rate: 1 slot from rate limiter.

    Returns MTProtoResult with data dict:
        id, title, username, about, members_count, entity_type,
        is_megagroup, is_broadcast, is_verified, is_scam, is_fake,
        date, linked_chat_id, has_photo
    """
    from telegram.telegram_client import (
        get_rate_limiter,
        get_telegram_client,
        run_async,
        _handle_telethon_error,
    )

    limiter = get_rate_limiter()
    if not limiter.acquire(timeout=15):
        return MTProtoResult(
            error="Rate limit — kutib turing", rate_limited=True,
        )

    try:
        client = get_telegram_client()

        async def _fetch():
            from telethon.tl.functions.channels import GetFullChannelRequest
            from telethon.tl.functions.messages import GetFullChatRequest
            from telethon.tl.types import Channel, Chat

            entity = await client.get_entity(int(entity_id))

            if isinstance(entity, Channel):
                full = await client(GetFullChannelRequest(entity))
                full_chat = full.full_chat
                return {
                    "id": entity.id,
                    "title": entity.title or "",
                    "username": entity.username or "",
                    "about": full_chat.about or "",
                    "members_count": full_chat.participants_count or 0,
                    "is_megagroup": entity.megagroup,
                    "is_broadcast": entity.broadcast,
                    "is_verified": entity.verified,
                    "is_scam": entity.scam,
                    "is_fake": entity.fake,
                    "date": entity.date.isoformat() if entity.date else None,
                    "linked_chat_id": full_chat.linked_chat_id,
                    "has_photo": entity.photo is not None,
                    "entity_type": (
                        "channel" if entity.broadcast else "supergroup"
                    ),
                }
            elif isinstance(entity, Chat):
                full = await client(GetFullChatRequest(entity.id))
                full_chat = full.full_chat
                return {
                    "id": entity.id,
                    "title": entity.title or "",
                    "username": "",
                    "about": full_chat.about or "",
                    "members_count": full_chat.participants_count or 0,
                    "is_megagroup": False,
                    "is_broadcast": False,
                    "is_verified": False,
                    "is_scam": False,
                    "is_fake": False,
                    "date": entity.date.isoformat() if entity.date else None,
                    "linked_chat_id": None,
                    "has_photo": entity.photo is not None,
                    "entity_type": "group",
                }
            else:
                return None  # User yoki boshqa — kanal/guruh emas

        result = run_async(_fetch())
        if result is None:
            return MTProtoResult(error="Bu entity kanal/guruh emas")

        # TelegramEntity ga saqlash
        _save_entity_to_db(result)

        return MTProtoResult(data=result)

    except RuntimeError as e:
        # get_telegram_client() xatolari (session yo'q, cooldown, etc.)
        return MTProtoResult(error=str(e))
    except Exception as e:
        error_msg = _handle_telethon_error(e, "entity_profile")
        return MTProtoResult(error=error_msg)


# ── Channel Messages ────────────────────────────────────────────────────────


def get_channel_messages(
    entity_id: int | str,
    limit: int = 20,
    offset_id: int = 0,
) -> MTProtoResult:
    """Get recent messages from a channel/group.

    Cursor-based pagination: offset_id = oxirgi xabar ID si.
    Keyingi sahifa uchun response dagi next_offset_id ni bering.

    Rate: 1 slot from rate limiter.
    Limit: Max 50 per request (hard cap).
    """
    from telegram.telegram_client import (
        get_rate_limiter,
        get_telegram_client,
        run_async,
        _handle_telethon_error,
    )

    limit = min(limit, 50)  # Xavfsizlik chegarasi

    limiter = get_rate_limiter()
    if not limiter.acquire(timeout=15):
        return MTProtoResult(
            error="Rate limit — kutib turing", rate_limited=True,
        )

    try:
        client = get_telegram_client()

        async def _fetch():
            messages = []
            async for msg in client.iter_messages(
                int(entity_id),
                limit=limit,
                offset_id=offset_id,
            ):
                messages.append(_serialize_message(msg))
            return messages

        result = run_async(_fetch())
        return MTProtoResult(data={
            "messages": result,
            "count": len(result),
            "has_more": len(result) == limit,
            "next_offset_id": result[-1]["id"] if result else 0,
        })

    except RuntimeError as e:
        return MTProtoResult(error=str(e))
    except Exception as e:
        error_msg = _handle_telethon_error(e, "channel_messages")
        return MTProtoResult(error=error_msg)


# ── Channel Message Search ──────────────────────────────────────────────────


def search_channel_messages(
    entity_id: int | str,
    query: str,
    limit: int = 20,
    offset_id: int = 0,
) -> MTProtoResult:
    """Search messages in a channel/group by text.

    Rate: 1 slot from rate limiter.
    Limit: Max 50 per request (hard cap).
    """
    from telegram.telegram_client import (
        get_rate_limiter,
        get_telegram_client,
        run_async,
        _handle_telethon_error,
    )

    limit = min(limit, 50)

    limiter = get_rate_limiter()
    if not limiter.acquire(timeout=15):
        return MTProtoResult(
            error="Rate limit — kutib turing", rate_limited=True,
        )

    try:
        client = get_telegram_client()

        async def _fetch():
            messages = []
            async for msg in client.iter_messages(
                int(entity_id),
                search=query,
                limit=limit,
                offset_id=offset_id,
            ):
                messages.append(_serialize_message(msg))
            return messages

        result = run_async(_fetch())
        return MTProtoResult(data={
            "messages": result,
            "count": len(result),
            "query": query,
            "has_more": len(result) == limit,
            "next_offset_id": result[-1]["id"] if result else 0,
        })

    except RuntimeError as e:
        return MTProtoResult(error=str(e))
    except Exception as e:
        error_msg = _handle_telethon_error(e, "channel_search")
        return MTProtoResult(error=error_msg)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _serialize_message(msg) -> dict:
    """Telethon Message ob'ektini JSON-serializable dict ga o'girish."""
    return {
        "id": msg.id,
        "date": msg.date.isoformat() if msg.date else None,
        "text": msg.text or "",
        "from_id": msg.sender_id,
        "views": msg.views,
        "forwards": msg.forwards,
        "reply_to_msg_id": (
            msg.reply_to.reply_to_msg_id if msg.reply_to else None
        ),
        "has_media": msg.media is not None,
        "media_type": _get_media_type(msg.media) if msg.media else None,
    }


def _get_media_type(media) -> str:
    """Detect media type from Telethon message.media object."""
    type_name = type(media).__name__
    media_map = {
        "MessageMediaPhoto": "photo",
        "MessageMediaDocument": "document",
        "MessageMediaWebPage": "webpage",
        "MessageMediaGeo": "location",
        "MessageMediaContact": "contact",
        "MessageMediaPoll": "poll",
        "MessageMediaDice": "dice",
        "MessageMediaVenue": "venue",
        "MessageMediaGame": "game",
        "MessageMediaInvoice": "invoice",
    }
    return media_map.get(type_name, "other")


def _save_entity_to_db(data: dict) -> None:
    """Profil natijasini TelegramEntity va EntitySource ga saqlash."""
    try:
        from telegram.models import EntitySource, TelegramEntity

        entity, _created = TelegramEntity.objects.update_or_create(
            telegram_id=data["id"],
            defaults={
                "entity_type": data.get("entity_type", "channel"),
                "title": data.get("title", ""),
                "username": data.get("username", ""),
                "bio": data.get("about", ""),
                "is_verified": data.get("is_verified", False),
                "is_scam": data.get("is_scam", False),
                "is_fake": data.get("is_fake", False),
            },
        )
        EntitySource.objects.get_or_create(
            entity=entity,
            service="osint",
            defaults={"role": "searched"},
        )
    except Exception as e:
        logger.warning("Entity DB ga saqlashda xatolik: %s", e)
