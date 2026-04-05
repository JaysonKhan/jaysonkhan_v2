"""Django admin views for bot management (polls, analytics, admins, users, universities).

All views accept a `svc` parameter from the URL (e.g. 'talabaovozi') which
selects which bot API to connect to via BOT_SERVICES settings.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from django.conf import settings as djsettings
from django.core.cache import cache
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from botproxy.client import BotAPIClient, BotAPIError
from core.decorators import admin_permission_required

logger = logging.getLogger(__name__)

PER_PAGE = 25


def _ctx(request, svc: str = "talabaovozi", extra: dict | None = None) -> dict:
    """Base context with admin site vars and service info."""
    _validate_svc(svc)
    from django.contrib import admin
    ctx = admin.site.each_context(request)
    ctx["svc"] = svc
    ctx["service_title"] = djsettings.BOT_SERVICES.get(svc, {}).get("title", svc)
    if extra:
        ctx.update(extra)
    return ctx


def _validate_svc(svc: str) -> None:
    """Raise Http404 if the service name is not in BOT_SERVICES."""
    if svc not in djsettings.BOT_SERVICES:
        raise Http404(f"Unknown bot service: {svc}")


def _client(svc: str = "talabaovozi") -> BotAPIClient:
    _validate_svc(svc)
    return BotAPIClient(service=svc)


def _handle_api_error(request, e: BotAPIError) -> None:
    if e.status == 0:
        messages.error(request, f"Bot serveriga ulanib bo'lmadi: {e.detail}")
    else:
        messages.error(request, f"Bot API xatosi ({e.status}): {e.detail}")


def _parse_page(request) -> int:
    """Extract and validate page number from request GET params."""
    try:
        page = int(request.GET.get("page", 1))
        return max(1, page)
    except (ValueError, TypeError):
        return 1


def _rev(name: str, svc: str, **kwargs) -> str:
    """Shortcut: reverse URL with svc parameter."""
    kwargs["svc"] = svc
    return reverse(name, kwargs=kwargs)


def _sanitize_url(url: str | None) -> str | None:
    """Ensure URL uses http/https protocol. Block javascript:, data: URIs and internal hosts."""
    if not url:
        return None
    url = url.strip()
    lower = url.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "file:")):
        return None
    if not lower.startswith(("http://", "https://")):
        url = "https://" + url
    # Block SSRF: reject localhost / internal IPs
    from urllib.parse import urlparse
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return None
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "") or host.endswith(".local"):
        return None
    if host.startswith(("10.", "192.168.", "169.254.")):
        return None
    if host.startswith("172.") and 16 <= int(host.split(".")[1]) <= 31:
        return None
    return url


def _detect_image_content_type(data: bytes) -> str:
    """Detect image content type from magic bytes."""
    if data[:5] == b"<?xml" or data[:4] == b"<svg" or b"<svg" in data[:256]:
        return "image/svg+xml"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


# ─── Dashboard ───────────────────────────────────────────────────────────────────

@admin_permission_required('botproxy.view_bot_dashboard')
def bot_dashboard(request, svc="talabaovozi"):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = _client(svc)
    ctx = {
        "api_ok": False, "polls": [], "user_count": 0, "admin_ids": [],
        "university_count": 0, "user_stats": {}, "growth_data": {},
        "audience_segments": [],
    }

    def _fetch(name, fn):
        try:
            return name, fn()
        except BotAPIError:
            return name, None

    tasks = {
        "health": lambda: client.health(),
        "polls": lambda: client.list_polls(),
        "user_count": lambda: client.get_user_count(),
        "admin_ids": lambda: client.list_admins(),
        "university_count": lambda: client.get_university_count(),
        "user_stats": lambda: client.get_user_stats(),
        "growth_data": lambda: client.get_user_growth_data(days=30),
        "audience_segments": lambda: client.get_audience_segments(),
    }

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch, k, v): k for k, v in tasks.items()}
        for f in as_completed(futures):
            name, result = f.result()
            if result is not None:
                if name == "health":
                    ctx["api_ok"] = result.get("status") == "ok"
                    ctx["active_polls"] = result.get("active_polls", 0)
                else:
                    ctx[name] = result

    ctx["active_polls_list"] = [p for p in ctx["polls"] if p.get("status") == "open"]
    ctx["growth_data_json"] = json.dumps(ctx.get("growth_data", {}))
    ctx["audience_segments_json"] = json.dumps(ctx.get("audience_segments", []))
    ctx["user_stats_json"] = json.dumps(ctx.get("user_stats", {}))

    return TemplateResponse(request, "botproxy/dashboard.html", _ctx(request, svc, ctx))


@admin_permission_required('botproxy.view_bot_dashboard')
def growth_data_api(request, svc="talabaovozi"):
    """AJAX: user growth data for period selector."""
    days = int(request.GET.get("days", "30"))
    if days not in (7, 14, 30, 90):
        days = 30
    client = _client(svc)
    try:
        data = client.get_user_growth_data(days=days)
    except BotAPIError:
        data = {"dates": [], "counts": [], "days": days}
    return JsonResponse(data)


@admin_permission_required('botproxy.view_bot_dashboard')
def poll_analytics_api(request, poll_id: int, svc="talabaovozi"):
    """AJAX: all analytics for a single poll."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = _client(svc)
    data = {}

    def _fetch(name, fn):
        try:
            return name, fn()
        except BotAPIError:
            return name, None

    tasks = {
        "by_date": lambda: client.get_votes_by_date(poll_id, days=30),
        "by_hour": lambda: client.get_votes_by_hour(poll_id),
        "by_faculty": lambda: client.get_votes_by_faculty(poll_id),
        "top": lambda: client.get_top(poll_id, limit=10),
        "results": lambda: client.get_results(poll_id),
    }

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch, k, v): k for k, v in tasks.items()}
        for f in as_completed(futures):
            name, result = f.result()
            data[name] = result

    return JsonResponse(data)


# ─── Polls ───────────────────────────────────────────────────────────────────────

@admin_permission_required('botproxy.view_bot_dashboard')
def poll_list(request, svc="talabaovozi"):
    client = _client(svc)
    polls = []
    try:
        polls = client.list_polls()
    except BotAPIError as e:
        _handle_api_error(request, e)

    # Annotate polls with university_name for display
    if any(p.get("university_id") for p in polls):
        try:
            unis = client.list_universities()
            uni_map = {u["id"]: u["short_name"] for u in unis}
            for p in polls:
                uid = p.get("university_id")
                p["university_name"] = uni_map.get(uid, "") if uid else ""
        except BotAPIError:
            pass

    return TemplateResponse(request, "botproxy/poll_list.html", _ctx(request, svc, {
        "polls": polls,
    }))


@admin_permission_required('botproxy.view_bot_dashboard')
def poll_detail(request, poll_id: int, svc="talabaovozi"):
    client = _client(svc)
    # Primary data — redirect if poll itself can't be fetched
    try:
        poll_data = client.get_poll(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_poll_list", svc))

    # Secondary data — show partial page if these fail
    results = {"total_voters": 0, "results": []}
    top = []
    try:
        results = client.get_results(poll_id)
    except BotAPIError as e:
        logger.warning("Failed to fetch results for poll %d: %s", poll_id, e)
    try:
        top = client.get_top(poll_id, limit=10).get("top", [])
    except BotAPIError as e:
        logger.warning("Failed to fetch top for poll %d: %s", poll_id, e)

    # Resolve university name if poll has university_id
    poll = poll_data["poll"]
    university = None
    if poll.get("university_id"):
        try:
            uni_data = client.get_university(poll["university_id"])
            university = uni_data.get("university")
        except BotAPIError:
            pass

    return TemplateResponse(request, "botproxy/poll_detail.html", _ctx(request, svc, {
        "poll": poll,
        "faculties": poll_data.get("faculties", []),
        "candidates": poll_data.get("candidates", []),
        "channels": poll_data.get("channels", []),
        "posts": poll_data.get("posts", []),
        "results": results,
        "top": top,
        "university": university,
    }))


@admin_permission_required('botproxy.manage_polls')
def poll_create(request, svc="talabaovozi"):
    client = _client(svc)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        deadline_at = request.POST.get("deadline_at", "").strip()
        university_id = request.POST.get("university_id", "").strip()

        # Parse faculties from JSON (dynamic form) or legacy textarea fallback
        faculties_json = request.POST.get("faculties_json", "").strip()
        if faculties_json:
            try:
                faculties = json.loads(faculties_json)  # [[code, name], ...]
            except (json.JSONDecodeError, TypeError):
                faculties = []
        else:
            faculties = []
            for line in request.POST.get("faculties", "").strip().splitlines():
                line = line.strip()
                if ":" in line:
                    code, name = line.split(":", 1)
                    faculties.append([code.strip(), name.strip()])

        # Parse candidates from JSON (dynamic form) or legacy textarea fallback
        candidates_json = request.POST.get("candidates_json", "").strip()
        if candidates_json:
            try:
                candidates = json.loads(candidates_json)  # [[fac_code, name, position?], ...]
            except (json.JSONDecodeError, TypeError):
                candidates = []
        else:
            candidates = []
            for line in request.POST.get("candidates", "").strip().splitlines():
                line = line.strip()
                if ":" in line:
                    parts = line.split(":", maxsplit=2)
                    candidates.append([p.strip() for p in parts])

        # Validate required fields before hitting the API
        if not title or not description or not deadline_at:
            messages.error(request, "Nomi, tavsif va muddati to'ldirilishi shart")
        elif not candidates:
            messages.error(request, "Kamida bitta nomzod kiritilishi kerak")
        else:
            try:
                max_votes = int(request.POST.get("max_votes_per_user", 1))
            except (ValueError, TypeError):
                max_votes = 1

            data = {
                "title": title,
                "description": description,
                "deadline_at": deadline_at,
                "max_votes_per_user": max_votes,
                "captcha_enabled": request.POST.get("captcha_enabled") == "on",
                "allow_vote_change": request.POST.get("allow_vote_change") == "on",
                "created_by": 0,  # admin panel sentinel (Django PK ≠ Telegram ID)
                "faculties": faculties,
                "candidates": candidates,
            }
            if university_id and university_id.isdigit():
                data["university_id"] = int(university_id)

            try:
                result = client.create_poll(data)
                messages.success(request, f"So'rovnoma yaratildi: {result['poll']['title']}")
                return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=result["poll"]["id"]))
            except BotAPIError as e:
                _handle_api_error(request, e)

    # GET: load universities for dropdown
    universities = []
    try:
        universities = client.list_universities()
    except BotAPIError:
        pass

    return TemplateResponse(request, "botproxy/poll_form.html", _ctx(request, svc, {
        "universities": universities,
    }))


@admin_permission_required('botproxy.manage_polls')
@require_POST
def poll_close(request, poll_id: int, svc="talabaovozi"):
    if True:  # @require_POST ensures POST-only
        client = _client(svc)
        try:
            client.close_poll(poll_id)
            messages.success(request, "So'rovnoma yopildi")
        except BotAPIError as e:
            _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))


@admin_permission_required('botproxy.manage_polls')
@require_POST
def poll_delete(request, poll_id: int, svc="talabaovozi"):
    if True:
        client = _client(svc)
        try:
            client.delete_poll(poll_id)
            messages.success(request, "So'rovnoma o'chirildi")
        except BotAPIError as e:
            _handle_api_error(request, e)
            return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))
    return HttpResponseRedirect(_rev("bot_poll_list", svc))


# ─── Publish ─────────────────────────────────────────────────────────────────────

@admin_permission_required('botproxy.manage_polls')
@require_POST
def poll_publish(request, poll_id: int, svc="talabaovozi"):
    if True:
        channel = request.POST.get("channel", "").strip()
        if not channel:
            messages.error(request, "Kanal kiritilmagan")
            return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))
        if not channel.startswith("@") and not channel.lstrip("-").isdigit():
            messages.error(request, "Kanal formati noto'g'ri. @username yoki ID kiriting.")
            return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))
        client = _client(svc)
        try:
            result = client.publish_poll(poll_id, channel)
            messages.success(request, f"Poll {channel} kanaliga muvaffaqiyatli joylandi!")
        except BotAPIError as e:
            _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))


# ─── Poll Channels ──────────────────────────────────────────────────────────────

@admin_permission_required('botproxy.manage_polls')
@require_POST
def poll_channel_add(request, poll_id: int, svc="talabaovozi"):
    if True:
        channel = request.POST.get("channel", "").strip()
        if not channel:
            messages.error(request, "Kanal kiritilmagan")
        elif not channel.startswith("@") and not channel.lstrip("-").isdigit():
            messages.error(request, "Kanal formati noto'g'ri. @username yoki ID kiriting.")
        else:
            client = _client(svc)
            try:
                client.add_poll_channel(poll_id, channel)
                messages.success(request, f"Majburiy kanal qo'shildi: {channel}")
            except BotAPIError as e:
                _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))


@admin_permission_required('botproxy.manage_polls')
@require_POST
def poll_channel_remove(request, poll_id: int, svc="talabaovozi"):
    if True:
        channel = request.POST.get("channel", "").strip()
        if channel:
            client = _client(svc)
            try:
                client.remove_poll_channel(poll_id, channel)
                messages.success(request, f"Kanal o'chirildi: {channel}")
            except BotAPIError as e:
                _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))


# ─── Poll Posts Refresh ─────────────────────────────────────────────────────────

@admin_permission_required('botproxy.manage_polls')
@require_POST
def poll_posts_refresh(request, poll_id: int, svc="talabaovozi"):
    if True:
        client = _client(svc)
        try:
            client.refresh_poll_posts(poll_id)
            messages.success(request, "Barcha kanal postlari muvaffaqiyatli yangilandi!")
        except BotAPIError as e:
            _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))


# ─── Export ──────────────────────────────────────────────────────────────────────

@admin_permission_required('botproxy.export_data')
def export_csv(request, poll_id: int, svc="talabaovozi"):
    client = _client(svc)
    try:
        data = client.export_csv(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))
    return HttpResponse(data, content_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="poll_{poll_id}.csv"'})


@admin_permission_required('botproxy.export_data')
def export_pdf(request, poll_id: int, svc="talabaovozi"):
    client = _client(svc)
    try:
        data = client.export_pdf(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))
    return HttpResponse(data, content_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="poll_{poll_id}_report.pdf"'})


@admin_permission_required('botproxy.export_data')
def export_json_view(request, poll_id: int, svc="talabaovozi"):
    client = _client(svc)
    try:
        data = client.export_json(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))
    return HttpResponse(data, content_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="poll_{poll_id}.json"'})


ALLOWED_CHART_TYPES = {"trend", "faculty", "hourly", "bar", "pie"}
ALLOWED_THEMES = {"", "light", "dark"}


@admin_permission_required('botproxy.view_bot_dashboard')
def poll_chart(request, poll_id: int, chart_type: str, svc="talabaovozi"):
    if chart_type not in ALLOWED_CHART_TYPES:
        return HttpResponse(status=400, content=b"Invalid chart type")
    theme = request.GET.get("theme", "")
    if theme not in ALLOWED_THEMES:
        theme = ""
    client = _client(svc)
    try:
        data = client.get_chart(poll_id, chart_type, theme=theme)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_poll_detail", svc, poll_id=poll_id))
    return HttpResponse(data, content_type="image/png")


# ─── Admins ──────────────────────────────────────────────────────────────────────

@admin_permission_required('botproxy.view_bot_dashboard')
def admin_list(request, svc="talabaovozi"):
    client = _client(svc)
    admins = []
    try:
        admins = client.list_admins_full()
    except BotAPIError as e:
        _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/admin_list.html", _ctx(request, svc, {"admins": admins}))


@admin_permission_required('botproxy.manage_bot_admins')
@require_POST
def admin_add(request, svc="talabaovozi"):
    if True:
        user_id = request.POST.get("user_id", "").strip()
        role = request.POST.get("role", "admin").strip()
        if role not in ("admin", "super_admin"):
            role = "admin"
        if user_id.isdigit():
            client = _client(svc)
            try:
                client.add_admin(int(user_id), added_by=0, role=role)  # admin panel sentinel
                role_label = "Bosh Admin" if role == "super_admin" else "Admin"
                messages.success(request, f"{role_label} qo'shildi: {user_id}")
            except BotAPIError as e:
                _handle_api_error(request, e)
        else:
            messages.error(request, "Telegram user ID raqam bo'lishi kerak")
    return HttpResponseRedirect(_rev("bot_admin_list", svc))


@admin_permission_required('botproxy.manage_bot_admins')
@require_POST
def admin_remove(request, user_id: int, svc="talabaovozi"):
    if True:
        client = _client(svc)
        try:
            client.remove_admin(user_id)
            messages.success(request, f"Admin o'chirildi: {user_id}")
        except BotAPIError as e:
            _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_admin_list", svc))


# ─── Users ───────────────────────────────────────────────────────────────────────

ALLOWED_SORT_FIELDS = {"name", "registered_at", "total_votes"}


@admin_permission_required('botproxy.view_bot_dashboard')
def user_stats(request, svc="talabaovozi"):
    """Users list with pagination, search, sort, and enhanced stats."""
    client = _client(svc)
    page = _parse_page(request)
    search = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "").strip()
    order = request.GET.get("order", "asc").strip()
    user_detail = None
    search_id = request.GET.get("user_id", "").strip()

    # Validate sort/order
    if sort not in ALLOWED_SORT_FIELDS:
        sort = ""
    if order not in ("asc", "desc"):
        order = "asc"

    # ── Enhanced stats ───────────────────────────────────────────────
    stats = {"total": 0, "today": 0, "this_week": 0, "this_month": 0, "active_voters": 0}
    try:
        stats = client.get_user_stats()
    except BotAPIError:
        logger.warning("get_user_stats failed (endpoint may not exist yet)")
        try:
            stats["total"] = client.get_user_count()
        except BotAPIError as e2:
            _handle_api_error(request, e2)

    user_count = stats.get("total", 0)

    # ── Paginated user list (with sort) ──────────────────────────────
    users = []
    total_pages = 1
    try:
        result = client.list_users(
            page=page, per_page=PER_PAGE, search=search,
            sort=sort, order=order,
        )
        users = result.get("users", [])
        user_count = result.get("total", user_count)
        total_pages = max(1, math.ceil(user_count / PER_PAGE))
    except BotAPIError as e:
        logger.warning("list_users failed: %s", e)

    # ── User detail search by ID → redirect to detail page ─────────
    if search_id and search_id.isdigit():
        try:
            user_detail = client.get_user_history(int(search_id))
        except BotAPIError:
            messages.warning(request, f"User {search_id} topilmadi")
        # If only user_id is searched (no text query), redirect directly
        if user_detail and not search:
            return HttpResponseRedirect(
                reverse("bot_user_detail", kwargs={"svc": svc, "user_id": int(search_id)})
            )

    page_range = _build_page_range(page, total_pages)

    return TemplateResponse(request, "botproxy/user_stats.html", _ctx(request, svc, {
        "stats": stats,
        "user_count": user_count,
        "users": users,
        "user_detail": user_detail,
        "search_id": search_id,
        "search_query": search,
        "sort": sort,
        "order": order,
        "page": page,
        "total_pages": total_pages,
        "page_range": page_range,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }))


@admin_permission_required('botproxy.view_bot_dashboard')
def user_detail(request, user_id: int, svc="talabaovozi"):
    """Unified user detail page — bot data + OSINT in one view."""
    client = _client(svc)

    # Bot data
    user_data = None
    try:
        user_data = client.get_user_history(user_id)
    except BotAPIError:
        pass

    # OSINT data (optional — only if user has osint permission)
    # NOTE: We only load cached data here. Fresh data is loaded via AJAX
    # when the OSINT tab is clicked (to avoid gunicorn timeout).
    osint_basic = None
    osint_tree = []
    has_osint = False
    try:
        from osint.models import OsintCache
        from osint.views import PROFILE_TREE

        if request.user.has_perm('osint.use_osint'):
            has_osint = True

            # Only use CACHED stats_min (no API call)
            cached_entry = OsintCache.get_cached("stats_min", str(user_id))
            if cached_entry:
                import json as _json
                try:
                    osint_basic = type('CachedResult', (), {
                        'data': _json.loads(cached_entry.data) if isinstance(cached_entry.data, str) else cached_entry.data,
                        'error': None,
                        'cached': True,
                    })()
                except Exception:
                    osint_basic = None

            cached_branches = set(
                OsintCache.objects.filter(target_id=str(user_id)).values_list(
                    "endpoint_type", flat=True
                )
            )
            for node in PROFILE_TREE:
                n = dict(node)
                n["has_cache"] = node["id"] in cached_branches
                if n["has_cache"]:
                    entry = OsintCache.get_cached(node["id"], str(user_id))
                    if entry:
                        n["cached_at"] = entry.fetched_at
                        n["is_stale"] = entry.is_stale
                osint_tree.append(n)
    except Exception:
        logger.warning("OSINT data unavailable for user %s", user_id, exc_info=True)

    return TemplateResponse(request, "botproxy/user_detail.html", _ctx(request, svc, {
        "user_detail": user_data,
        "user_id": user_id,
        "has_osint": has_osint,
        "osint_basic": osint_basic,
        "osint_tree": osint_tree,
    }))


@admin_permission_required('botproxy.view_bot_dashboard')
def user_photo_proxy(request, user_id: int, svc="talabaovozi"):
    """Proxy user profile photo from bot API."""
    client = _client(svc)
    try:
        photo_bytes = client.get_user_photo(user_id)
    except Exception:
        logger.warning("user_photo_proxy xatolik (user_id=%s)", user_id, exc_info=True)
        return HttpResponse(status=502)
    if not photo_bytes:
        return HttpResponse(status=404)
    return HttpResponse(
        photo_bytes,
        content_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@admin_permission_required('botproxy.view_bot_dashboard')
def user_growth_chart(request, svc="talabaovozi"):
    """Proxy user growth chart PNG from bot API."""
    theme = request.GET.get("theme", "")
    if theme not in ALLOWED_THEMES:
        theme = ""
    client = _client(svc)
    try:
        data = client.get_user_growth_chart(days=30, theme=theme)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_user_stats", svc))
    return HttpResponse(data, content_type="image/png")


@admin_permission_required('botproxy.export_data')
def export_users_csv(request, svc="talabaovozi"):
    """Download all users as CSV."""
    client = _client(svc)
    try:
        data = client.export_users_csv()
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_user_stats", svc))
    return HttpResponse(data, content_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="users.csv"'})


# ─── Universities ───────────────────────────────────────────────────────────────

REGIONS = [
    "Toshkent", "Toshkent viloyati", "Samarqand", "Buxoro",
    "Andijon", "Farg'ona", "Namangan", "Xorazm", "Navoiy",
    "Qashqadaryo", "Surxondaryo", "Jizzax", "Sirdaryo", "Qoraqalpog'iston",
]


def _logo_dir(svc: str) -> Path:
    """Return the directory for cached university logo files."""
    d = Path(djsettings.MEDIA_ROOT) / "uni_logos" / svc
    d.mkdir(parents=True, exist_ok=True)
    return d


def _logo_disk_path(svc: str, uni_id: int) -> Path | None:
    """Return the on-disk path of a cached logo, or None if not yet downloaded."""
    d = _logo_dir(svc)
    for ext in ("png", "jpg", "svg", "webp"):
        p = d / f"{uni_id}.{ext}"
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


_EXT_MAP = {"image/png": "png", "image/jpeg": "jpg", "image/svg+xml": "svg", "image/webp": "webp"}


def _save_logo_to_disk(svc: str, uni_id: int, logo_bytes: bytes) -> Path:
    """Save logo bytes to disk and return the file path."""
    content_type = _detect_image_content_type(logo_bytes)
    ext = _EXT_MAP.get(content_type, "png")
    path = _logo_dir(svc) / f"{uni_id}.{ext}"
    path.write_bytes(logo_bytes)
    return path


def _warmup_logos_to_disk(svc: str, uni_ids: list[int]) -> None:
    """Background task: download missing logos to disk (non-blocking)."""
    from concurrent.futures import ThreadPoolExecutor
    client = _client(svc)

    def _fetch_one(uni_id: int) -> None:
        if _logo_disk_path(svc, uni_id):
            return  # already on disk
        try:
            logo_bytes = client.get_university_logo(uni_id)
        except Exception:
            return
        if logo_bytes:
            _save_logo_to_disk(svc, uni_id, logo_bytes)

    with ThreadPoolExecutor(max_workers=3) as pool:
        pool.map(_fetch_one, uni_ids)


@admin_permission_required('botproxy.view_bot_dashboard')
def university_list(request, svc="talabaovozi"):
    import threading

    client = _client(svc)
    region_filter = request.GET.get("region", "").strip()
    universities = []
    try:
        universities = client.list_universities(region=region_filter or None)
    except BotAPIError as e:
        _handle_api_error(request, e)

    # Annotate each university with a direct media URL if logo exists on disk
    media_url = djsettings.MEDIA_URL  # e.g. /media/
    for uni in universities:
        if uni.get("logo_path"):
            disk = _logo_disk_path(svc, uni["id"])
            if disk:
                uni["logo_url"] = f"{media_url}uni_logos/{svc}/{disk.name}"
            else:
                uni["logo_url"] = None  # will use proxy fallback
        else:
            uni["logo_url"] = None

    # Non-blocking: download missing logos to disk in background
    missing = [u["id"] for u in universities if u.get("logo_path") and not u.get("logo_url")]
    if missing:
        t = threading.Thread(target=_warmup_logos_to_disk, args=(svc, missing), daemon=True)
        t.start()

    return TemplateResponse(request, "botproxy/university_list.html", _ctx(request, svc, {
        "universities": universities,
        "regions": REGIONS,
        "selected_region": region_filter,
    }))


@admin_permission_required('botproxy.view_bot_dashboard')
def university_detail(request, uni_id: int, svc="talabaovozi"):
    client = _client(svc)
    try:
        data = client.get_university(uni_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_university_list", svc))

    # Get polls for this university
    polls = []
    try:
        all_polls = client.list_polls()
        polls = [p for p in all_polls if p.get("university_id") == uni_id]
    except BotAPIError:
        pass

    # Handle faculty add/remove (requires manage_universities permission)
    if request.method == "POST":
        if not request.user.is_superuser and not request.user.has_perm('botproxy.manage_universities'):
            raise PermissionDenied
        action = request.POST.get("action", "")
        if action == "add_faculty":
            code = request.POST.get("fac_code", "").strip()
            name = request.POST.get("fac_name", "").strip()
            if code and name:
                try:
                    client.add_university_faculty(uni_id, code, name)
                    messages.success(request, f"Fakultet qo'shildi: {code}")
                except BotAPIError as e:
                    _handle_api_error(request, e)
            else:
                messages.error(request, "Kod va nom kiritilishi shart")
            return HttpResponseRedirect(_rev("bot_university_detail", svc, uni_id=uni_id))
        elif action == "remove_faculty":
            fac_id = request.POST.get("fac_id", "")
            if fac_id and fac_id.isdigit():
                try:
                    client.remove_university_faculty(int(fac_id))
                    messages.success(request, "Fakultet o'chirildi")
                except BotAPIError as e:
                    _handle_api_error(request, e)
            return HttpResponseRedirect(_rev("bot_university_detail", svc, uni_id=uni_id))

    return TemplateResponse(request, "botproxy/university_detail.html", _ctx(request, svc, {
        "uni": data.get("university", {}),
        "faculties": data.get("faculties", []),
        "polls": polls,
    }))


@admin_permission_required('botproxy.manage_universities')
def university_create(request, svc="talabaovozi"):
    client = _client(svc)
    if request.method == "POST":
        data = {
            "code": request.POST.get("code", "").strip(),
            "short_name": request.POST.get("short_name", "").strip(),
            "full_name": request.POST.get("full_name", "").strip(),
            "bio": request.POST.get("bio", "").strip() or None,
            "website": _sanitize_url(request.POST.get("website", "").strip() or None),
            "region": request.POST.get("region", "").strip() or None,
        }
        est_year = request.POST.get("established_year", "").strip()
        if est_year and est_year.isdigit():
            data["established_year"] = int(est_year)

        if not data["code"] or not data["short_name"] or not data["full_name"]:
            messages.error(request, "Kod, qisqa nom va to'liq nom kiritilishi shart")
        else:
            try:
                result = client.create_university(data)
                uni = result.get("university", {})
                uni_id = uni.get("id")

                # Upload logo if provided (max 5MB)
                logo_file = request.FILES.get("logo")
                if logo_file and uni_id:
                    if logo_file.size > 5 * 1024 * 1024:
                        messages.warning(request, "Universitet yaratildi, lekin logo 5MB dan katta")
                    else:
                        try:
                            client.upload_university_logo(uni_id, logo_file.read(), logo_file.name)
                        except BotAPIError:
                            messages.warning(request, "Universitet yaratildi, lekin logo yuklanmadi")

                messages.success(request, f"Universitet yaratildi: {uni.get('short_name', '')}")
                if uni_id:
                    return HttpResponseRedirect(_rev("bot_university_detail", svc, uni_id=uni_id))
                return HttpResponseRedirect(_rev("bot_university_list", svc))
            except BotAPIError as e:
                _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/university_form.html", _ctx(request, svc, {
        "regions": REGIONS,
        "edit_mode": False,
    }))


@admin_permission_required('botproxy.manage_universities')
def university_edit(request, uni_id: int, svc="talabaovozi"):
    client = _client(svc)
    try:
        uni_data = client.get_university(uni_id)
        uni = uni_data.get("university", {})
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_university_list", svc))

    if request.method == "POST":
        data = {
            "code": request.POST.get("code", "").strip(),
            "short_name": request.POST.get("short_name", "").strip(),
            "full_name": request.POST.get("full_name", "").strip(),
            "bio": request.POST.get("bio", "").strip() or None,
            "website": _sanitize_url(request.POST.get("website", "").strip() or None),
            "region": request.POST.get("region", "").strip() or None,
        }
        est_year = request.POST.get("established_year", "").strip()
        if est_year and est_year.isdigit():
            data["established_year"] = int(est_year)

        if not data["code"] or not data["short_name"] or not data["full_name"]:
            messages.error(request, "Kod, qisqa nom va to'liq nom kiritilishi shart")
        else:
            try:
                client.update_university(uni_id, data)
                # Upload new logo if provided (max 5MB)
                logo_file = request.FILES.get("logo")
                if logo_file:
                    if logo_file.size > 5 * 1024 * 1024:
                        messages.warning(request, "Ma'lumot yangilandi, lekin logo 5MB dan katta")
                    else:
                        try:
                            client.upload_university_logo(uni_id, logo_file.read(), logo_file.name)
                        except BotAPIError:
                            messages.warning(request, "Ma'lumot yangilandi, lekin logo yuklanmadi")

                messages.success(request, "Universitet yangilandi")
                return HttpResponseRedirect(_rev("bot_university_detail", svc, uni_id=uni_id))
            except BotAPIError as e:
                _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/university_form.html", _ctx(request, svc, {
        "uni": uni,
        "regions": REGIONS,
        "edit_mode": True,
    }))


@admin_permission_required('botproxy.manage_universities')
@require_POST
def university_delete(request, uni_id: int, svc="talabaovozi"):
    if True:
        client = _client(svc)
        try:
            client.delete_university(uni_id)
            messages.success(request, "Universitet o'chirildi")
        except BotAPIError as e:
            _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_university_list", svc))


@admin_permission_required('botproxy.view_bot_dashboard')
def university_logo_proxy(request, uni_id: int, svc="talabaovozi"):
    """Proxy university logo: serve from disk if cached, otherwise fetch + save."""
    _LOGO_HEADERS = {
        "Cache-Control": "public, max-age=3600",
        "X-Content-Type-Options": "nosniff",
    }
    # 1. Check disk first (fastest, no gunicorn blocking)
    disk = _logo_disk_path(svc, uni_id)
    if disk:
        data = disk.read_bytes()
        ct = _detect_image_content_type(data[:16])
        return HttpResponse(data, content_type=ct, headers=_LOGO_HEADERS)

    # 2. Fetch from bot API
    client = _client(svc)
    try:
        logo_bytes = client.get_university_logo(uni_id)
    except BotAPIError:
        logger.warning("Logo proxy: bot API error for uni_id=%s", uni_id, exc_info=True)
        return HttpResponse(status=502)
    except Exception:
        logger.exception("Logo proxy: unexpected error for uni_id=%s", uni_id)
        return HttpResponse(status=500)

    if not logo_bytes:
        return HttpResponse(status=404)

    # 3. Save to disk for future nginx serving
    _save_logo_to_disk(svc, uni_id, logo_bytes)
    content_type = _detect_image_content_type(logo_bytes)
    return HttpResponse(logo_bytes, content_type=content_type, headers=_LOGO_HEADERS)


@admin_permission_required('botproxy.view_bot_dashboard')
def university_faculties_api(request, uni_id: int, svc="talabaovozi"):
    """AJAX endpoint: return university faculties as JSON for poll form auto-fill."""
    client = _client(svc)
    try:
        faculties = client.list_university_faculties(uni_id)
    except BotAPIError:
        faculties = []
    return JsonResponse({"faculties": faculties})


@admin_permission_required('botproxy.manage_universities')
@require_POST
def faculty_edit(request, fac_id: int, svc="talabaovozi"):
    """AJAX endpoint: update faculty code/name."""
    client = _client(svc)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Noto'g'ri JSON format"}, status=400)
    try:
        client.update_university_faculty(
            fac_id,
            code=data.get("code"),
            name=data.get("name"),
            sort_order=data.get("sort_order"),
        )
        return JsonResponse({"status": "ok"})
    except BotAPIError as e:
        return JsonResponse({"error": e.detail}, status=e.status or 400)


def _build_page_range(current: int, total: int) -> list:
    """Build a compact page range with ellipsis markers."""
    if total <= 7:
        return list(range(1, total + 1))

    pages = []
    if current <= 4:
        pages = list(range(1, 6)) + [None, total]
    elif current >= total - 3:
        pages = [1, None] + list(range(total - 4, total + 1))
    else:
        pages = [1, None, current - 1, current, current + 1, None, total]
    return pages


# ─── Staff Management ──────────────────────────────────────────────────────────


@admin_permission_required('botproxy.view_bot_dashboard')
def staff_list(request, svc="talabaovozi"):
    client = _client(svc)
    university_id = request.GET.get("university_id")
    staff = []
    universities = []
    try:
        staff = client.list_staff(
            university_id=int(university_id) if university_id else None
        )
        universities = client.list_universities()
    except BotAPIError as e:
        _handle_api_error(request, e)

    # Annotate with university name
    uni_map = {u["id"]: u["short_name"] for u in universities}
    for s in staff:
        s["university_name"] = uni_map.get(s.get("university_id"), "—")

    ctx = {
        "staff": staff,
        "universities": universities,
        "selected_university": int(university_id) if university_id else None,
    }
    return TemplateResponse(request, "botproxy/staff_list.html", _ctx(request, svc, ctx))


@admin_permission_required('botproxy.view_bot_dashboard')
def staff_create(request, svc="talabaovozi"):
    client = _client(svc)

    if request.method == "POST":
        data = {
            "university_id": int(request.POST["university_id"]),
            "full_name": request.POST["full_name"],
            "position": request.POST["position"],
            "department": request.POST.get("department", "").strip() or None,
            "phone": request.POST.get("phone", "").strip() or None,
            "email": request.POST.get("email", "").strip() or None,
            "bio": request.POST.get("bio", "").strip() or None,
            "reception_hours": request.POST.get("reception_hours", "").strip() or None,
        }
        try:
            result = client.create_staff(data)
            staff_id = result.get("id")
            # Upload photo if provided
            photo = request.FILES.get("photo")
            if photo and staff_id:
                client.upload_staff_photo(staff_id, photo.read(), photo.name)
            messages.success(request, f"Xodim qo'shildi: {data['full_name']}")
            return HttpResponseRedirect(_rev("bot_staff_list", svc))
        except BotAPIError as e:
            _handle_api_error(request, e)

    universities = []
    try:
        universities = client.list_universities()
    except BotAPIError:
        pass

    return TemplateResponse(request, "botproxy/staff_form.html", _ctx(request, svc, {
        "universities": universities,
        "form_title": "Yangi xodim qo'shish",
        "submit_text": "Qo'shish",
    }))


@admin_permission_required('botproxy.view_bot_dashboard')
def staff_detail(request, staff_id: int, svc="talabaovozi"):
    client = _client(svc)
    try:
        staff = client.get_staff(staff_id)
        feedback = client.list_feedback_by_staff(staff_id)
        summary = client.get_staff_feedback_summary(staff_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_staff_list", svc))

    return TemplateResponse(request, "botproxy/staff_detail.html", _ctx(request, svc, {
        "staff": staff,
        "feedback_list": feedback,
        "summary": summary,
    }))


@admin_permission_required('botproxy.view_bot_dashboard')
def staff_edit(request, staff_id: int, svc="talabaovozi"):
    client = _client(svc)

    if request.method == "POST":
        data = {
            "full_name": request.POST["full_name"],
            "position": request.POST["position"],
            "department": request.POST.get("department", "").strip() or None,
            "phone": request.POST.get("phone", "").strip() or None,
            "email": request.POST.get("email", "").strip() or None,
            "bio": request.POST.get("bio", "").strip() or None,
            "reception_hours": request.POST.get("reception_hours", "").strip() or None,
        }
        try:
            client.update_staff(staff_id, data)
            photo = request.FILES.get("photo")
            if photo:
                client.upload_staff_photo(staff_id, photo.read(), photo.name)
            messages.success(request, "Xodim yangilandi")
            return HttpResponseRedirect(_rev("bot_staff_detail", svc, staff_id=staff_id))
        except BotAPIError as e:
            _handle_api_error(request, e)

    try:
        staff = client.get_staff(staff_id)
        universities = client.list_universities()
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(_rev("bot_staff_list", svc))

    return TemplateResponse(request, "botproxy/staff_form.html", _ctx(request, svc, {
        "staff": staff,
        "universities": universities,
        "form_title": f"Tahrirlash: {staff.get('full_name', '')}",
        "submit_text": "Saqlash",
        "edit_mode": True,
    }))


@admin_permission_required('botproxy.view_bot_dashboard')
@require_POST
def staff_delete(request, staff_id: int, svc="talabaovozi"):
    client = _client(svc)
    try:
        client.delete_staff(staff_id)
        messages.success(request, "Xodim o'chirildi")
    except BotAPIError as e:
        _handle_api_error(request, e)
    return HttpResponseRedirect(_rev("bot_staff_list", svc))


@admin_permission_required('botproxy.view_bot_dashboard')
def staff_photo_proxy(request, staff_id: int, svc="talabaovozi"):
    """Serve staff photo from bot API."""
    client = _client(svc)
    data = client.get_staff_photo(staff_id)
    if not data:
        raise Http404("No photo")
    content_type = _detect_image_content_type(data)
    return HttpResponse(data, content_type=content_type)


# ─── Feedback Dashboard ──────────────────────────────────────────────────────


@admin_permission_required('botproxy.view_bot_dashboard')
def feedback_dashboard(request, svc="talabaovozi"):
    client = _client(svc)
    polls = []
    summaries = {}
    try:
        polls = client.list_polls()
        for poll in polls:
            try:
                summaries[poll["id"]] = client.get_feedback_summary(poll["id"])
            except BotAPIError:
                summaries[poll["id"]] = {"total": 0, "positive": 0, "negative": 0}
    except BotAPIError as e:
        _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/feedback_dashboard.html", _ctx(request, svc, {
        "polls": polls,
        "summaries": summaries,
    }))
