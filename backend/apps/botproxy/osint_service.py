"""Service layer for OSINT operations — cache-aware data fetching."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
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


def resolve_and_search(query: str, user=None) -> dict:
    """Resolve query to a Telegram user_id.

    - Numeric → direct user ID (free)
    - @username → resolve_username API call (cost 0.10)
    """
    query = query.strip()

    if query.isdigit():
        OsintSearchLog.objects.update_or_create(
            query=query,
            query_type="id",
            searched_by=user,
            defaults={
                "resolved_id": int(query),
                "searched_at": timezone.now(),
            },
        )
        return {"user_id": int(query), "error": None, "tech": {}, "cost": 0}

    # Username
    username = query.lstrip("@")
    if not username:
        return {"user_id": None, "error": "Bo'sh so'rov", "tech": {}, "cost": 0}

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

        OsintSearchLog.objects.update_or_create(
            query=query,
            query_type="username",
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
            "error": None if resolved_id else f"'{username}' topilmadi",
            "tech": tech,
            "cost": tech.get("request_cost", 0),
        }
    except FunStatAPIError as e:
        return {"user_id": None, "error": str(e), "tech": {}, "cost": 0}
    except Exception as e:
        logger.exception("Unexpected error resolving username: %s", e)
        return {"user_id": None, "error": str(e), "tech": {}, "cost": 0}
