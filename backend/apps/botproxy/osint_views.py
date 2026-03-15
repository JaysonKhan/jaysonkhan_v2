"""OSINT views for FunStat Telegram intelligence."""
from __future__ import annotations

import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from django.utils import timezone

from botproxy.funstat_client import FunStatClient, FunStatAPIError
from botproxy.models import OsintCache, OsintSearchLog
from botproxy.osint_service import (
    ENDPOINT_REGISTRY,
    fetch_channel_data,
    fetch_or_cache,
    resolve_and_search,
)

logger = logging.getLogger(__name__)


def _ctx(request, extra: dict | None = None) -> dict:
    """Base context for OSINT views."""
    from django.contrib import admin

    ctx = admin.site.each_context(request)
    ctx["is_osint"] = True
    if extra:
        ctx.update(extra)
    return ctx


# ── Profile tree definition ──────────────────────────────────────────────────

PROFILE_TREE = [
    {"id": "stats_min",          "label": "Asosiy ma'lumotlar",          "icon": "person",          "cost": "Bepul",     "auto_load": True},
    {"id": "stats_full",         "label": "To'liq statistika",          "icon": "analytics",       "cost": "1 kredit",  "auto_load": False},
    {"id": "groups",             "label": "Guruhlar",                    "icon": "groups",          "cost": "5 kredit",  "auto_load": False},
    {"id": "names",              "label": "Ism tarixi",                  "icon": "history",         "cost": "3 kredit",  "auto_load": False},
    {"id": "usernames",          "label": "Username tarixi",             "icon": "alternate_email", "cost": "3 kredit",  "auto_load": False},
    {"id": "stickers",           "label": "Stiker paketlari",           "icon": "emoji_emotions",  "cost": "1 kredit",  "auto_load": False},
    {"id": "gifts",              "label": "Sovg'a aloqalari",           "icon": "redeem",          "cost": "5 kredit",  "auto_load": False, "paginated": True},
    {"id": "common_groups_stat", "label": "Umumiy guruhlar statistikasi","icon": "hub",             "cost": "5 kredit",  "auto_load": False},
    {"id": "messages",           "label": "Xabarlar",                    "icon": "chat",            "cost": "10 kredit", "auto_load": False, "paginated": True},
]


# ─── Search Page ──────────────────────────────────────────────────────────────

@staff_member_required
def osint_search(request):
    """Search by Telegram ID or @username — routes to user or entity profile."""
    query = request.GET.get("q", "").strip()
    error = None

    if query:
        result = resolve_and_search(query, user=request.user)
        if result["user_id"]:
            entity_type = result.get("entity_type", "user")
            if entity_type in ("channel", "supergroup", "group"):
                return redirect(
                    reverse("osint_entity_profile", kwargs={"entity_id": result["user_id"]})
                )
            # Default: user/bot → existing profile
            return redirect(
                reverse("osint_profile", kwargs={"user_id": result["user_id"]})
            )
        error = result["error"] or f"'{query}' topilmadi"

    recent = (
        OsintSearchLog.objects.filter(searched_by=request.user)
        .select_related("searched_by")[:15]
    )

    return TemplateResponse(
        request,
        "botproxy/osint_search.html",
        _ctx(request, {"query": query, "error": error, "recent_searches": recent}),
    )


# ─── Profile Page ─────────────────────────────────────────────────────────────

@staff_member_required
def osint_profile(request, user_id: int):
    """User profile page with lazy-loading tree."""
    # Log this visit so it appears in "So'nggi qidiruvlar"
    OsintSearchLog.objects.update_or_create(
        query=str(user_id),
        query_type="id",
        searched_by=request.user,
        defaults={
            "resolved_id": user_id,
            "searched_at": timezone.now(),
        },
    )

    basic = fetch_or_cache("stats_min", user_id, user=request.user)

    # Check which branches have cached data
    cached_branches = set(
        OsintCache.objects.filter(target_id=str(user_id)).values_list(
            "endpoint_type", flat=True
        )
    )

    tree = []
    for node in PROFILE_TREE:
        n = dict(node)
        n["has_cache"] = node["id"] in cached_branches
        if n["has_cache"]:
            entry = OsintCache.get_cached(node["id"], str(user_id))
            if entry:
                n["cached_at"] = entry.fetched_at
                n["is_stale"] = entry.is_stale
        tree.append(n)

    return TemplateResponse(
        request,
        "botproxy/osint_profile.html",
        _ctx(request, {
            "user_id": user_id,
            "basic": basic,
            "tree": tree,
            "balance": basic.tech.get("current_ballance") if basic.tech and isinstance(basic.tech, dict) else None,
        }),
    )


# ─── AJAX: Fetch Branch ──────────────────────────────────────────────────────

@staff_member_required
def osint_fetch_branch(request, user_id: int, branch: str):
    """AJAX: fetch a specific tree branch. ?refresh=1 to force re-fetch."""
    if branch not in ENDPOINT_REGISTRY:
        return JsonResponse({"error": "Noma'lum bo'lim"}, status=400)

    force = request.GET.get("refresh") == "1"
    page = max(1, int(request.GET.get("page", 1)))

    result = fetch_or_cache(
        endpoint_type=branch,
        target_id=user_id,
        page=page,
        force_refresh=force,
        user=request.user,
    )

    if result.error:
        return JsonResponse({"error": result.error}, status=502)

    return JsonResponse({
        "data": result.data,
        "tech": result.tech,
        "cached": result.cached,
        "cached_at": result.cached_at,
    })


# ─── AJAX: Text Search ───────────────────────────────────────────────────────

@staff_member_required
def osint_text_search(request):
    """AJAX: text search across messages."""
    query = request.GET.get("q", "").strip()
    page = max(1, int(request.GET.get("page", 1)))

    if not query:
        return JsonResponse({"error": "Qidiruv so'zi kiritilmagan"}, status=400)

    client = FunStatClient()
    try:
        resp = client.text_search(query, page=page)
    except FunStatAPIError as e:
        return JsonResponse({"error": str(e)}, status=502)

    # Smart parse response
    if isinstance(resp, dict) and "data" in resp:
        resp_data = resp["data"]
        resp_tech = resp.get("tech", {})
    else:
        resp_data = resp if resp is not None else {}
        resp_tech = {}

    OsintSearchLog.objects.update_or_create(
        query=query,
        query_type="text",
        searched_by=request.user,
        defaults={
            "searched_at": timezone.now(),
            "api_cost": resp_tech.get("request_cost", 0),
            "balance_after": resp_tech.get("current_ballance"),
        },
    )

    return JsonResponse({
        "data": resp_data,
        "tech": resp_tech,
    })


# ─── Entity Profile (Channel/Group) ──────────────────────────────────────

@staff_member_required
def osint_entity_profile(request, entity_id: int):
    """Kanal/guruh profil sahifasi — Telethon MTProto + FunStat get_group_info."""
    # Log this visit
    OsintSearchLog.objects.update_or_create(
        query=str(entity_id),
        query_type="channel",
        searched_by=request.user,
        defaults={
            "resolved_id": entity_id,
            "searched_at": timezone.now(),
        },
    )

    # Telethon MTProto profil
    profile = fetch_channel_data(
        operation="channel_profile",
        entity_id=entity_id,
        user=request.user,
    )

    # FunStat group_info (qo'shimcha ma'lumot — 0.01 kredit)
    funstat_info = None
    try:
        funstat_info = fetch_or_cache(
            "group_info", entity_id, user=request.user,
        )
    except Exception:
        pass

    return TemplateResponse(
        request,
        "botproxy/osint_entity_profile.html",
        _ctx(request, {
            "entity_id": entity_id,
            "profile": profile,
            "funstat_info": funstat_info,
        }),
    )


@staff_member_required
def osint_channel_messages(request, entity_id: int):
    """AJAX: kanal/guruh xabarlari (offset_id cursor pagination)."""
    offset_id = max(0, int(request.GET.get("offset_id", 0)))
    limit = min(50, max(1, int(request.GET.get("limit", 20))))
    force = request.GET.get("refresh") == "1"

    result = fetch_channel_data(
        operation="channel_messages",
        entity_id=entity_id,
        offset_id=offset_id,
        limit=limit,
        force_refresh=force,
        user=request.user,
    )

    if result.error:
        return JsonResponse({"error": result.error}, status=502)

    return JsonResponse({
        "data": result.data,
        "cached": result.cached,
        "cached_at": result.cached_at,
    })


@staff_member_required
def osint_channel_search(request, entity_id: int):
    """AJAX: kanal ichida xabar qidirish."""
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"error": "Qidiruv so'zi kiritilmagan"}, status=400)

    offset_id = max(0, int(request.GET.get("offset_id", 0)))
    limit = min(50, max(1, int(request.GET.get("limit", 20))))

    result = fetch_channel_data(
        operation="channel_search",
        entity_id=entity_id,
        query=query,
        offset_id=offset_id,
        limit=limit,
        user=request.user,
    )

    if result.error:
        return JsonResponse({"error": result.error}, status=502)

    return JsonResponse({
        "data": result.data,
        "cached": result.cached,
        "cached_at": result.cached_at,
    })


# ─── Message Photo Proxy ──────────────────────────────────────────────────────

@staff_member_required
def osint_message_photo(request, entity_id: int, msg_id: int):
    """Serve photo from a channel/group message.

    Telethon orqali yuklab olinadi, faylga keshlanadi.
    Browser cache: 24 soat.
    """
    from telegram.mtproto_service import get_message_photo

    result = get_message_photo(entity_id, msg_id)
    if result.error or not result.data:
        return HttpResponse(status=404)

    # Detect content type from magic bytes
    data = result.data
    if data[:3] == b"\xff\xd8\xff":
        ct = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        ct = "image/png"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ct = "image/webp"
    else:
        ct = "image/jpeg"

    return HttpResponse(
        data,
        content_type=ct,
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ─── Photo Proxy ─────────────────────────────────────────────────────────────

@staff_member_required
def osint_photo_proxy(request, entity_id: str):
    """Serve cached Telegram profile photo for any entity (user/group/channel/bot).

    URL: osint/photo/<entity_id>/
    Query: ?refresh=1 to force re-download from Telegram.

    Returns:
      - JPEG with browser caching (1 hour) if local cache hit
      - 302 redirect to entity's photo_url if local cache miss but external URL exists
      - 404 if no photo available at all
      - 503 if Telegram client unavailable
    """
    # entity_id ni tozalash (path traversal himoya)
    clean_id = entity_id.strip().lstrip("-")
    if not clean_id.isdigit():
        return HttpResponse(status=400)

    from telegram.photo_service import get_entity_photo

    force = request.GET.get("refresh") == "1"

    try:
        photo_bytes, content_type = get_entity_photo(entity_id, force_refresh=force)
    except RuntimeError as e:
        logger.warning("Telegram photo xizmati mavjud emas: %s", e)
        return HttpResponse(status=503)

    if photo_bytes and content_type:
        return HttpResponse(
            photo_bytes,
            content_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    # Fallback: redirect to entity's external photo_url (e.g. Telegram avatar)
    try:
        from telegram.models import TelegramEntity

        entity_obj = TelegramEntity.objects.filter(
            telegram_id=int(entity_id),
        ).only("photo_url").first()
        if entity_obj and entity_obj.photo_url:
            return redirect(entity_obj.photo_url)
    except (ValueError, TypeError):
        pass

    return HttpResponse(status=404)


# ─── AJAX: Balance ───────────────────────────────────────────────────────────

@staff_member_required
def osint_balance(request):
    """AJAX: return last known FunStat balance from cached API responses."""
    # Try to find balance from the most recent cache entry that has tech data
    for entry in OsintCache.objects.exclude(tech={}).order_by("-fetched_at")[:10]:
        if isinstance(entry.tech, dict) and entry.tech.get("current_ballance") is not None:
            return JsonResponse({"balance": entry.tech["current_ballance"]})

    # Try from search log balance_after
    log = OsintSearchLog.objects.filter(
        balance_after__isnull=False,
    ).order_by("-searched_at").first()
    if log:
        return JsonResponse({"balance": float(log.balance_after)})

    return JsonResponse({"balance": None})
