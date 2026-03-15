"""Service layer for OSINT operations — cache-aware data fetching.

FunStat (user OSINT) + Telethon MTProto (kanal/guruh operatsiyalari) uchun
yagona service layer. Barcha natijalar OsintCache orqali keshlanadi.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.utils import timezone

from botproxy.funstat_client import FunStatClient, FunStatAPIError
from botproxy.models import OsintCache, OsintSearchLog

logger = logging.getLogger(__name__)


@dataclass
class OsintResult:
    """Wrapper for cached or fresh OSINT data."""
    data: Any = None
    tech: dict = field(default_factory=dict)
    cached: bool = False
    cached_at: str | None = None
    error: str | None = None


# endpoint_type → (client_method_name, cost_label, paginated?)
ENDPOINT_REGISTRY: dict[str, tuple[str, str, bool]] = {
    "stats_min":          ("get_user_stats_min",      "Bepul",     False),
    "groups_count":       ("get_user_groups_count",    "Bepul",     False),
    "messages_count":     ("get_user_messages_count",  "Bepul",     False),
    "stats_full":         ("get_user_stats_full",      "1 kredit",  False),
    "groups":             ("get_user_groups",          "5 kredit",  False),
    "names":              ("get_user_names",           "3 kredit",  False),
    "usernames":          ("get_user_usernames",       "3 kredit",  False),
    "stickers":           ("get_user_stickers",        "1 kredit",  False),
    "gifts":              ("get_user_gifts",           "5 kredit",  True),
    "common_groups_stat": ("get_user_common_groups",   "5 kredit",  False),
    "messages":           ("get_user_messages",        "10 kredit", True),
    "group_info":         ("get_group_info",           "0.01 kredit", False),
}

# Telethon operatsiyalari uchun TTL (soatlarda)
CHANNEL_CACHE_TTL = {
    "channel_profile": 24,   # Profil — 24 soat
    "channel_messages": 1,   # Xabarlar — 1 soat
    "channel_search": 0.5,   # Qidirish — 30 daqiqa
}


def fetch_or_cache(
    endpoint_type: str,
    target_id: str | int,
    page: int = 1,
    force_refresh: bool = False,
    user=None,
) -> OsintResult:
    """Check cache first; if miss or stale or forced, call API and cache result."""
    target_str = str(target_id)

    # 1. Try cache
    if not force_refresh:
        cached = OsintCache.get_cached(endpoint_type, target_str, page)
        if cached and not cached.is_stale:
            return OsintResult(
                data=cached.data,
                tech=cached.tech,
                cached=True,
                cached_at=cached.fetched_at.isoformat(),
            )

    # 2. Fetch from API
    reg = ENDPOINT_REGISTRY.get(endpoint_type)
    if not reg:
        return OsintResult(error=f"Noma'lum endpoint: {endpoint_type}")

    method_name, _cost_label, is_paginated = reg
    client = FunStatClient()
    method = getattr(client, method_name)

    try:
        if is_paginated:
            response = method(int(target_id), page=page)
        else:
            response = method(int(target_id))
    except FunStatAPIError as e:
        return OsintResult(error=str(e))
    except Exception as e:
        logger.exception("Unexpected error calling FunStat API: %s", e)
        return OsintResult(error=f"API xatoligi: {e}")

    # Smart parsing: some endpoints wrap in {"data": ..., "tech": ...},
    # others return data directly at the top level.
    if isinstance(response, dict) and "data" in response:
        api_data = response["data"]
        api_tech = response.get("tech", {})
    else:
        api_data = response if response is not None else {}
        api_tech = {}

    # 3. Store in cache
    entry = OsintCache.set_cache(
        endpoint_type=endpoint_type,
        target_id=target_str,
        data=api_data,
        tech=api_tech,
        page=page,
        user=user,
    )

    return OsintResult(
        data=api_data,
        tech=api_tech,
        cached=False,
        cached_at=entry.fetched_at.isoformat(),
    )


def fetch_channel_data(
    operation: str,
    entity_id: int | str,
    force_refresh: bool = False,
    query: str = "",
    offset_id: int = 0,
    limit: int = 20,
    user=None,
) -> OsintResult:
    """Telethon MTProto operatsiyalari uchun cache-aware data fetching.

    Operations:
        channel_profile — kanal/guruh profili (TTL: 24 soat)
        channel_messages — xabarlar ro'yxati (TTL: 1 soat)
        channel_search — xabar qidirish (TTL: 30 daqiqa)

    Cache key: (endpoint_type, target_id, page=1)
    Search uchun target_id = "entity_id:query" (offset_id har xil bo'lgani uchun page=1)
    """
    entity_str = str(entity_id)
    ttl_hours = CHANNEL_CACHE_TTL.get(operation, 24)

    # Cache key — search uchun query ni ham qo'shish
    if operation == "channel_search":
        cache_target = f"{entity_str}:{query}"
    else:
        cache_target = entity_str

    # Offset/pagination uchun page sifatida offset_id ishlatamiz
    # (0 = birinchi sahifa, keyingilar uchun offset_id)
    cache_page = max(1, offset_id)

    # 1. Try cache (faqat birinchi sahifa uchun va force emas bo'lsa)
    if not force_refresh and offset_id == 0:
        cached = OsintCache.get_cached(operation, cache_target, page=1)
        if cached:
            age = timezone.now() - cached.fetched_at
            if age < timedelta(hours=ttl_hours):
                return OsintResult(
                    data=cached.data,
                    tech=cached.tech,
                    cached=True,
                    cached_at=cached.fetched_at.isoformat(),
                )

    # 2. Fetch from Telethon MTProto
    from telegram.mtproto_service import (
        get_channel_messages,
        get_entity_profile,
        search_channel_messages,
    )

    if operation == "channel_profile":
        result = get_entity_profile(entity_id)
    elif operation == "channel_messages":
        result = get_channel_messages(entity_id, limit=limit, offset_id=offset_id)
    elif operation == "channel_search":
        result = search_channel_messages(entity_id, query=query, limit=limit, offset_id=offset_id)
    else:
        return OsintResult(error=f"Noma'lum operatsiya: {operation}")

    if result.error:
        return OsintResult(error=result.error)

    # 3. Cache the result (faqat birinchi sahifa va profil uchun)
    api_data = result.data or {}
    tech_info = {"source": "telethon_mtproto"}

    if operation == "channel_profile" or offset_id == 0:
        entry = OsintCache.set_cache(
            endpoint_type=operation,
            target_id=cache_target,
            data=api_data,
            tech=tech_info,
            page=1,
            user=user,
        )
        cached_at = entry.fetched_at.isoformat()
    else:
        cached_at = timezone.now().isoformat()

    return OsintResult(
        data=api_data,
        tech=tech_info,
        cached=False,
        cached_at=cached_at,
    )


# ── Entity Type Detection ──────────────────────────────────────────────────


def _detect_entity_type(entity_id: int) -> str | None:
    """DB dan entity turini aniqlash (API chaqiruvsiz).

    Returns: 'user', 'bot', 'group', 'supergroup', 'channel', or None.
    """
    try:
        from telegram.models import TelegramEntity
        entity = TelegramEntity.objects.filter(
            telegram_id=entity_id,
        ).only("entity_type").first()
        if entity:
            return entity.entity_type
    except Exception:
        pass
    return None


def _resolve_via_telethon(username: str) -> dict | None:
    """Telethon orqali username ni resolve qilish (FunStat fallback).

    Returns dict: {id, entity_type, title/first_name, username} or None.
    Rate limited — faqat FunStat topolmaganda ishlatiladi.
    """
    try:
        from telegram.telegram_client import (
            get_rate_limiter,
            get_telegram_client,
            run_async,
            _handle_telethon_error,
        )

        limiter = get_rate_limiter()
        if not limiter.acquire(timeout=10):
            logger.warning("Telethon resolve rate limited: @%s", username)
            return None

        client = get_telegram_client()

        async def _resolve():
            from telethon.tl.types import Channel, Chat, User
            entity = await client.get_entity(username)
            if isinstance(entity, Channel):
                return {
                    "id": entity.id,
                    "entity_type": "channel" if entity.broadcast else "supergroup",
                    "title": entity.title or "",
                    "username": entity.username or "",
                }
            elif isinstance(entity, Chat):
                return {
                    "id": entity.id,
                    "entity_type": "group",
                    "title": entity.title or "",
                    "username": "",
                }
            elif isinstance(entity, User):
                return {
                    "id": entity.id,
                    "entity_type": "bot" if entity.bot else "user",
                    "first_name": entity.first_name or "",
                    "last_name": entity.last_name or "",
                    "username": entity.username or "",
                }
            return None

        result = run_async(_resolve())

        # DB ga saqlash — FAQAT kanal/guruh uchun (PeerChannel/PeerChat hints uchun kerak).
        # User/bot entitylarini saqlaMAYMIZ — ular faqat saytga login qilganda yaratiladi.
        if result and result["entity_type"] in ("channel", "supergroup", "group"):
            from telegram.models import EntitySource, TelegramEntity

            entity_obj, _ = TelegramEntity.objects.update_or_create(
                telegram_id=result["id"],
                defaults={
                    "entity_type": result["entity_type"],
                    "username": result.get("username", ""),
                    "title": result.get("title", ""),
                },
            )
            EntitySource.objects.get_or_create(
                entity=entity_obj,
                service="osint",
                defaults={"role": "searched"},
            )

        return result

    except RuntimeError as e:
        logger.warning("Telethon resolve xatolik (@%s): %s", username, e)
        return None
    except Exception as e:
        logger.warning("Telethon resolve xatolik (@%s): %s", username, e)
        return None


def resolve_and_search(query: str, user=None) -> dict:
    """Resolve query to a Telegram entity (user, channel, group).

    - Numeric → direct entity ID (free) + entity_type from DB
    - @username → FunStat resolve → Telethon fallback
    - Returns entity_type for routing (user/bot → profile, channel/group → entity_profile)
    """
    query = query.strip()

    if query.isdigit():
        entity_id = int(query)
        entity_type = _detect_entity_type(entity_id) or "user"

        OsintSearchLog.objects.update_or_create(
            query=query,
            query_type="channel" if entity_type in ("channel", "supergroup", "group") else "id",
            searched_by=user,
            defaults={
                "resolved_id": entity_id,
                "searched_at": timezone.now(),
            },
        )
        return {
            "user_id": entity_id,
            "entity_type": entity_type,
            "error": None,
            "tech": {},
            "cost": 0,
        }

    # Username
    username = query.lstrip("@")
    if not username:
        return {"user_id": None, "entity_type": None, "error": "Bo'sh so'rov", "tech": {}, "cost": 0}

    # 1. FunStat orqali resolve qilish
    client = FunStatClient()
    try:
        resp = client.resolve_username(username)

        # Response might be {"data": [...], "tech": {...}} or direct data
        if isinstance(resp, dict) and "data" in resp:
            tech = resp.get("tech", {})
            data = resp["data"]
        elif isinstance(resp, list):
            tech = {}
            data = resp
        elif isinstance(resp, dict):
            tech = {}
            data = resp
        else:
            tech = {}
            data = []

        # data could be a list of resolved_user or a single object
        resolved_id = None
        if isinstance(data, list) and data:
            resolved_id = data[0].get("id") if isinstance(data[0], dict) else None
        elif isinstance(data, dict):
            resolved_id = data.get("id")

        if resolved_id:
            entity_type = _detect_entity_type(resolved_id) or "user"
            OsintSearchLog.objects.update_or_create(
                query=query,
                query_type="channel" if entity_type in ("channel", "supergroup", "group") else "username",
                searched_by=user,
                defaults={
                    "resolved_id": resolved_id,
                    "searched_at": timezone.now(),
                    "api_cost": tech.get("request_cost", 0),
                    "balance_after": tech.get("current_ballance"),
                },
            )
            return {
                "user_id": resolved_id,
                "entity_type": entity_type,
                "error": None,
                "tech": tech,
                "cost": tech.get("request_cost", 0),
            }

    except FunStatAPIError:
        pass
    except Exception as e:
        logger.warning("FunStat resolve xatolik (@%s): %s", username, e)

    # 2. Telethon fallback — FunStat topolmagan entitylarni Telethon bilan resolve
    telethon_result = _resolve_via_telethon(username)
    if telethon_result:
        resolved_id = telethon_result["id"]
        entity_type = telethon_result["entity_type"]

        OsintSearchLog.objects.update_or_create(
            query=query,
            query_type="channel" if entity_type in ("channel", "supergroup", "group") else "username",
            searched_by=user,
            defaults={
                "resolved_id": resolved_id,
                "searched_at": timezone.now(),
                "api_cost": 0,
            },
        )
        return {
            "user_id": resolved_id,
            "entity_type": entity_type,
            "error": None,
            "tech": {"source": "telethon"},
            "cost": 0,
        }

    return {
        "user_id": None,
        "entity_type": None,
        "error": f"'{username}' topilmadi",
        "tech": {},
        "cost": 0,
    }
