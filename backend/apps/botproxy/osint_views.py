"""OSINT views for FunStat Telegram intelligence."""
from __future__ import annotations

import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from botproxy.funstat_client import FunStatClient, FunStatAPIError
from botproxy.models import OsintCache, OsintSearchLog
from botproxy.osint_service import (
    ENDPOINT_REGISTRY,
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
    """Search by Telegram ID or @username."""
    query = request.GET.get("q", "").strip()
    error = None

    if query:
        result = resolve_and_search(query, user=request.user)
        if result["user_id"]:
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
            "balance": basic.tech.get("current_ballance") if basic.tech else None,
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

    OsintSearchLog.objects.create(
        query=query,
        query_type="text",
        searched_by=request.user,
        api_cost=resp.get("tech", {}).get("request_cost", 0),
        balance_after=resp.get("tech", {}).get("current_ballance"),
    )

    return JsonResponse({
        "data": resp.get("data", {}),
        "tech": resp.get("tech", {}),
    })


# ─── AJAX: Balance ───────────────────────────────────────────────────────────

@staff_member_required
def osint_balance(request):
    """AJAX: check current FunStat balance (uses free reputation endpoint)."""
    client = FunStatClient()
    try:
        # Use one of the free test IDs to get tech.current_ballance
        resp = client.get_user_stats_min(8104838448)
        return JsonResponse({
            "balance": resp.get("tech", {}).get("current_ballance"),
        })
    except FunStatAPIError as e:
        return JsonResponse({"error": str(e)}, status=502)
