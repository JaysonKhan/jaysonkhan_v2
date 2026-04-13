"""On-demand single-user enrichment via Telethon.

Called from user_detail view when admin opens a user profile.
Enriches once, caches result — no mass scraping, no background loops.

Usage:
    from botproxy.enrich_service import enrich_user_on_view
    enrich_user_on_view(user_id, username, bot_client)
"""
from __future__ import annotations

import json
import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache key prefix — prevents re-enriching same user within cooldown
_CACHE_PREFIX = "enrich_user:"
_COOLDOWN_SECONDS = 3600  # 1 soat — bitta user uchun qayta enrich qilmaslik


def enrich_user_on_view(
    user_id: int,
    username: str | None,
    bot_client,
) -> dict | None:
    """Enrich a single user via Telethon when admin views their profile.

    Returns enrichment data dict on success, None on skip/error.
    Silently skips if:
        - Already enriched within cooldown period
        - Telethon session not available
        - Any error (never blocks the page load)
    """
    cache_key = f"{_CACHE_PREFIX}{user_id}"

    # Skip if recently enriched
    if cache.get(cache_key):
        return None

    try:
        data = _fetch_and_save(user_id, username, bot_client)
        if data:
            # Mark as enriched in cache
            cache.set(cache_key, True, _COOLDOWN_SECONDS)
        return data
    except Exception:
        logger.debug("Enrich skip for user %s", user_id, exc_info=True)
        # Set a shorter cooldown on error to avoid hammering
        cache.set(cache_key, True, 300)  # 5 min on error
        return None


def _fetch_and_save(
    user_id: int,
    username: str | None,
    bot_client,
) -> dict | None:
    """Fetch user data via Telethon and save via bot API."""
    from telegram.telegram_client import get_telegram_client, run_async

    try:
        tg_client = get_telegram_client()
    except RuntimeError:
        # No session configured — silently skip
        return None

    data = _fetch_user_data(tg_client, user_id, username)

    if data is None:
        # User not found on Telegram
        _save_to_bot_api(bot_client, user_id, {
            "enrichment_source": "telethon_not_found",
        })
        return None

    if data == "NOT_RESOLVED":
        _save_to_bot_api(bot_client, user_id, {
            "enrichment_source": "no_access_hash",
        })
        return None

    # Save enrichment data
    _save_to_bot_api(bot_client, user_id, data)
    return data


def _save_to_bot_api(bot_client, user_id: int, data: dict) -> bool:
    """Save enrichment data via bot API PATCH endpoint."""
    try:
        bot_client._request("PATCH", f"/api/v1/users/{user_id}/enrich", json=data)
        return True
    except Exception:
        logger.debug("Failed to save enrich data for user %s", user_id)
        return False


def _fetch_user_data(client, user_id: int, username: str | None) -> dict | str | None:
    """Fetch full user data from Telegram via Telethon.

    Returns:
        dict — enrichment data
        "NOT_RESOLVED" — user exists but can't be resolved
        None — user not found
    """
    from telegram.telegram_client import run_async

    async def _get_full_user():
        from telethon.tl.functions.users import GetFullUserRequest
        from telethon.tl.types import (
            InputPeerUser,
            UserStatusOnline,
            UserStatusOffline,
            UserStatusRecently,
            UserStatusLastWeek,
            UserStatusLastMonth,
        )
        from telethon.errors import FloodWaitError

        entity = None
        resolve_method = "unknown"

        # Try username first
        if username:
            try:
                entity = await client.get_input_entity(f"@{username}")
                resolve_method = "username"
            except FloodWaitError:
                raise
            except Exception:
                pass

        # Try user_id from cache
        if entity is None:
            try:
                entity = await client.get_input_entity(user_id)
                resolve_method = "cache"
            except FloodWaitError:
                raise
            except Exception:
                pass

        # Try zero access hash
        if entity is None:
            try:
                entity = InputPeerUser(user_id, access_hash=0)
                await client(GetFullUserRequest(entity))
                resolve_method = "zero_hash"
            except FloodWaitError:
                raise
            except Exception as e:
                err_str = str(e).lower()
                err_type = type(e).__name__.lower()
                if any(x in err_str or x in err_type for x in (
                    "could not find", "input entity", "user_id_invalid",
                    "peer_id_invalid", "useridinvalid",
                )):
                    return "NOT_RESOLVED"
                raise

        try:
            full_result = await client(GetFullUserRequest(entity))
        except FloodWaitError:
            raise
        except Exception as e:
            err_str = str(e).lower()
            err_type = type(e).__name__.lower()
            if any(x in err_str or x in err_type for x in (
                "user_id_invalid", "peer_id_invalid", "input_user_deactivated",
                "useridinvalid",
            )):
                return None
            raise

        full_user = full_result.full_user
        user_obj = None
        for u in full_result.users:
            if u.id == user_id:
                user_obj = u
                break
        if not user_obj:
            return None

        data = {"enrichment_source": f"telethon:{resolve_method}"}

        if full_user.about:
            data["bio"] = full_user.about
        data["is_premium"] = 1 if getattr(user_obj, "premium", False) else 0
        data["is_deleted"] = 1 if getattr(user_obj, "deleted", False) else 0
        data["is_bot"] = 1 if getattr(user_obj, "bot", False) else 0
        if getattr(user_obj, "lang_code", None):
            data["language_code"] = user_obj.lang_code
        if getattr(user_obj, "photo", None) and hasattr(user_obj.photo, "dc_id"):
            data["dc_id"] = user_obj.photo.dc_id
        if hasattr(full_user, "common_chats_count"):
            data["common_chats_count"] = full_user.common_chats_count

        status = getattr(user_obj, "status", None)
        if isinstance(status, UserStatusOnline):
            data["last_online_at"] = status.expires.isoformat() if status.expires else None
        elif isinstance(status, UserStatusOffline):
            data["last_online_at"] = status.was_online.isoformat() if status.was_online else None
        elif isinstance(status, UserStatusRecently):
            data["last_online_at"] = "recently"
        elif isinstance(status, UserStatusLastWeek):
            data["last_online_at"] = "last_week"
        elif isinstance(status, UserStatusLastMonth):
            data["last_online_at"] = "last_month"

        if user_obj.first_name:
            data["first_name"] = user_obj.first_name
        if user_obj.last_name:
            data["last_name"] = user_obj.last_name
        if user_obj.username:
            data["username"] = user_obj.username

        usernames = []
        if user_obj.username:
            usernames.append(user_obj.username)
        if hasattr(user_obj, "usernames") and user_obj.usernames:
            for un in user_obj.usernames:
                uname = getattr(un, "username", None)
                if uname and uname not in usernames:
                    usernames.append(uname)
        if usernames:
            data["usernames_json"] = json.dumps(usernames)

        if getattr(user_obj, "phone", None):
            phone = user_obj.phone
            if not phone.startswith("+"):
                phone = f"+{phone}"
            data["phone2"] = phone

        return data

    return run_async(_get_full_user())
