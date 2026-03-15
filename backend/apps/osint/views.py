"""OSINT views for FunStat Telegram intelligence."""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone

from osint.exceptions import FunStatAPIError
from osint.models import OsintCache, OsintSearchLog
from osint.services.funstat_client import FunStatClient
from osint.services.osint_service import (
    ENDPOINT_REGISTRY,
    fetch_channel_data,
    fetch_or_cache,
    resolve_and_search,
)

logger = logging.getLogger(__name__)


def _detect_image_content_type(data: bytes) -> str:
    """Rasm baytlaridan content-type ni aniqlash (magic bytes)."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and len(data) > 11 and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _normalize_entity_id(raw: str | int) -> int | None:
    """Telegram entity ID ni normalizatsiya qilish."""
    try:
        n = int(raw)
    except (ValueError, TypeError):
        return None
    if n < 0:
        s = str(abs(n))
        if s.startswith("100") and len(s) > 10:
            return int(s[3:])
        return abs(n)
    return n


def _ctx(request, extra: dict | None = None) -> dict:
    """Base context for OSINT views."""
    from django.contrib import admin

    ctx = admin.site.each_context(request)
    ctx["is_osint"] = True
    if extra:
        ctx.update(extra)
    return ctx


def _annotate_search_logs(logs: list) -> None:
    """Har bir OsintSearchLog ga entity_name va has_photo qo'shish."""
    if not logs:
        return

    resolved_ids = [s.resolved_id for s in logs if s.resolved_id]
    if not resolved_ids:
        for s in logs:
            s.entity_name = s.query
            s.has_photo = False
        return

    # 1. TelegramEntity dan nomlar
    from telegram.models import TelegramEntity

    entities = {
        e.telegram_id: e
        for e in TelegramEntity.objects.filter(
            telegram_id__in=resolved_ids,
        ).only("telegram_id", "first_name", "last_name", "title", "username", "entity_type", "has_photo")
    }

    # 2. OsintCache dan nomlar (stats_min yoki channel_profile)
    cache_names: dict[int, str] = {}
    cache_entries = OsintCache.objects.filter(
        endpoint_type__in=("stats_min", "channel_profile"),
        target_id__in=[str(rid) for rid in resolved_ids],
        page=1,
    ).only("target_id", "endpoint_type", "data")

    for entry in cache_entries:
        try:
            tid = int(entry.target_id)
        except (ValueError, TypeError):
            continue
        if tid in cache_names:
            continue
        data = entry.data or {}
        if entry.endpoint_type == "stats_min":
            parts = [data.get("first_name") or "", data.get("last_name") or ""]
            name = " ".join(p for p in parts if p).strip()
            if not name:
                name = data.get("name") or data.get("username") or ""
            if name:
                cache_names[tid] = name
        elif entry.endpoint_type == "channel_profile":
            name = data.get("title") or data.get("name") or ""
            if name:
                cache_names[tid] = name

    # 3. Annotate
    for s in logs:
        s.has_photo = False
        s.entity_name = ""
        s.entity_username = ""  # photo proxy username fallback uchun

        if not s.resolved_id:
            s.entity_name = s.query
            continue

        rid = s.resolved_id
        entity = entities.get(rid)

        if entity:
            s.has_photo = entity.has_photo
            s.entity_username = entity.username or ""
            if entity.entity_type in ("channel", "supergroup", "group"):
                s.entity_name = entity.title or entity.username or ""
            else:
                parts = [entity.first_name or "", entity.last_name or ""]
                s.entity_name = " ".join(p for p in parts if p).strip()
                if not s.entity_name:
                    s.entity_name = entity.username or ""

        # OsintCache fallback
        if not s.entity_name and rid in cache_names:
            s.entity_name = cache_names[rid]
            s.has_photo = True

        # Final fallback
        if not s.entity_name:
            s.entity_name = s.query


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
            return redirect(
                reverse("osint_profile", kwargs={"user_id": result["user_id"]})
            )
        error = result["error"] or f"'{query}' topilmadi"

    recent = list(
        OsintSearchLog.objects.filter(searched_by=request.user)
        .select_related("searched_by")[:15]
    )
    _annotate_search_logs(recent)

    return TemplateResponse(
        request,
        "osint/osint_search.html",
        _ctx(request, {"query": query, "error": error, "recent_searches": recent}),
    )


# ─── Profile Page ─────────────────────────────────────────────────────────────

@staff_member_required
def osint_profile(request, user_id: int):
    """User profile page with lazy-loading tree."""
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
        "osint/osint_profile.html",
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
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

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
def osint_entity_profile(request, entity_id: str):
    """Kanal/guruh profil sahifasi."""
    eid = _normalize_entity_id(entity_id)
    if eid is None:
        return HttpResponse("Noto'g'ri entity ID", status=400)

    OsintSearchLog.objects.update_or_create(
        query=str(eid),
        query_type="channel",
        searched_by=request.user,
        defaults={
            "resolved_id": eid,
            "searched_at": timezone.now(),
        },
    )

    profile = fetch_channel_data(
        operation="channel_profile",
        entity_id=eid,
        user=request.user,
    )

    if profile.error and (
        "PeerUser" in (profile.error or "")
        or "kanal/guruh emas" in (profile.error or "")
    ):
        OsintSearchLog.objects.filter(
            query=str(eid),
            query_type="channel",
            searched_by=request.user,
        ).update(query_type="id")
        return redirect(
            reverse("osint_profile", kwargs={"user_id": eid})
        )

    funstat_info = None
    try:
        funstat_info = fetch_or_cache(
            "group_info", eid, user=request.user,
        )
    except Exception:
        pass

    return TemplateResponse(
        request,
        "osint/osint_entity_profile.html",
        _ctx(request, {
            "entity_id": eid,
            "profile": profile,
            "funstat_info": funstat_info,
        }),
    )


@staff_member_required
def osint_channel_messages(request, entity_id: str):
    """AJAX: kanal/guruh xabarlari (offset_id cursor pagination)."""
    eid = _normalize_entity_id(entity_id)
    if eid is None:
        return JsonResponse({"error": "Noto'g'ri entity ID"}, status=400)
    try:
        offset_id = max(0, int(request.GET.get("offset_id", 0)))
        limit = min(50, max(1, int(request.GET.get("limit", 20))))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Noto'g'ri parametr"}, status=400)
    force = request.GET.get("refresh") == "1"

    result = fetch_channel_data(
        operation="channel_messages",
        entity_id=eid,
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
def osint_channel_search(request, entity_id: str):
    """AJAX: kanal ichida xabar qidirish."""
    eid = _normalize_entity_id(entity_id)
    if eid is None:
        return JsonResponse({"error": "Noto'g'ri entity ID"}, status=400)
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"error": "Qidiruv so'zi kiritilmagan"}, status=400)
    try:
        offset_id = max(0, int(request.GET.get("offset_id", 0)))
        limit = min(50, max(1, int(request.GET.get("limit", 20))))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Noto'g'ri parametr"}, status=400)

    result = fetch_channel_data(
        operation="channel_search",
        entity_id=eid,
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
def osint_message_photo(request, entity_id: str, msg_id: int):
    """Serve photo from a channel/group message."""
    from telegram.mtproto_service import get_message_photo

    eid = _normalize_entity_id(entity_id)
    if eid is None:
        return HttpResponse(status=400)
    result = get_message_photo(eid, msg_id)
    if result.error or not result.data:
        return HttpResponse(status=404)

    data = result.data
    ct = _detect_image_content_type(data)
    return HttpResponse(
        data,
        content_type=ct,
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ─── Photo Proxy ─────────────────────────────────────────────────────────────

@staff_member_required
def osint_photo_proxy(request, entity_id: str):
    """Serve cached Telegram profile photo for any entity."""
    from pathlib import Path

    from django.core.cache import cache

    from telegram.models import TelegramEntity
    from telegram.photo_service import _try_stale_cache, get_entity_photo

    clean_id = str(entity_id).strip().lstrip("-")
    if not clean_id.isdigit():
        return HttpResponse(status=400)

    force = request.GET.get("refresh") == "1"
    username = request.GET.get("u", "").strip().lstrip("@")[:64]

    # 1. Negative cache
    neg_cache_key = f"osint_photo_neg:{clean_id}"
    if not force and cache.get(neg_cache_key):
        return HttpResponse(status=404)

    # 2. Fast path: DB + disk cache
    if not force:
        try:
            entity_obj = TelegramEntity.objects.filter(
                telegram_id=int(clean_id),
            ).only("photo_file", "photo_url", "has_photo").first()

            if entity_obj:
                if entity_obj.has_photo is False:
                    return HttpResponse(status=404)

                if entity_obj.photo_file:
                    abs_path = Path(settings.MEDIA_ROOT) / entity_obj.photo_file
                    if abs_path.exists():
                        data = abs_path.read_bytes()
                        if len(data) > 100:
                            ct = _detect_image_content_type(data)
                            return HttpResponse(
                                data,
                                content_type=ct,
                                headers={"Cache-Control": "public, max-age=3600"},
                            )

                if entity_obj.photo_url:
                    return redirect(entity_obj.photo_url)
        except Exception:
            pass

    # 3. Full photo service (Bot API + Telethon)
    try:
        photo_bytes, content_type = get_entity_photo(
            clean_id, force_refresh=force, username=username,
        )
    except RuntimeError as e:
        logger.warning("Telegram photo xizmati mavjud emas: %s", e)
        stale_bytes, stale_ct = _try_stale_cache(clean_id)
        if stale_bytes:
            return HttpResponse(
                stale_bytes,
                content_type=stale_ct,
                headers={"Cache-Control": "public, max-age=300"},
            )
        return HttpResponse(status=503)

    if photo_bytes and content_type:
        return HttpResponse(
            photo_bytes,
            content_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    # Negative cache
    cache.set(neg_cache_key, True, 86400)
    return HttpResponse(status=404)


# ─── AJAX: Balance ───────────────────────────────────────────────────────────

@staff_member_required
def osint_balance(request):
    """AJAX: return last known FunStat balance."""
    for entry in OsintCache.objects.exclude(tech={}).order_by("-fetched_at")[:10]:
        if isinstance(entry.tech, dict) and entry.tech.get("current_ballance") is not None:
            return JsonResponse({"balance": entry.tech["current_ballance"]})

    log = OsintSearchLog.objects.filter(
        balance_after__isnull=False,
    ).order_by("-searched_at").first()
    if log:
        return JsonResponse({"balance": float(log.balance_after)})

    return JsonResponse({"balance": None})
