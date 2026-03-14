"""Django admin views for Rektor Bot management (polls, analytics, admins, users)."""
from __future__ import annotations

import logging
import math

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse

from botproxy.client import BotAPIClient, BotAPIError

logger = logging.getLogger(__name__)

PER_PAGE = 25


def _ctx(request, extra: dict | None = None) -> dict:
    """Base context with admin site vars."""
    from django.contrib import admin
    ctx = admin.site.each_context(request)
    if extra:
        ctx.update(extra)
    return ctx


def _client() -> BotAPIClient:
    return BotAPIClient()


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


# ─── Dashboard ───────────────────────────────────────────────────────────────────

@staff_member_required
def bot_dashboard(request):
    client = _client()
    ctx = {"api_ok": False, "polls": [], "user_count": 0, "admin_ids": []}
    try:
        health = client.health()
        ctx["api_ok"] = health.get("status") == "ok"
        ctx["active_polls"] = health.get("active_polls", 0)
        ctx["polls"] = client.list_polls()
        ctx["user_count"] = client.get_user_count()
        ctx["admin_ids"] = client.list_admins()
    except BotAPIError as e:
        _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/dashboard.html", _ctx(request, ctx))


# ─── Polls ───────────────────────────────────────────────────────────────────────

@staff_member_required
def poll_list(request):
    client = _client()
    polls = []
    try:
        polls = client.list_polls()
    except BotAPIError as e:
        _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/poll_list.html", _ctx(request, {"polls": polls}))


@staff_member_required
def poll_detail(request, poll_id: int):
    client = _client()
    # Primary data — redirect if poll itself can't be fetched
    try:
        poll_data = client.get_poll(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_poll_list"))

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

    return TemplateResponse(request, "botproxy/poll_detail.html", _ctx(request, {
        "poll": poll_data["poll"],
        "faculties": poll_data.get("faculties", []),
        "candidates": poll_data.get("candidates", []),
        "channels": poll_data.get("channels", []),
        "results": results,
        "top": top,
    }))


@staff_member_required
def poll_create(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        deadline_at = request.POST.get("deadline_at", "").strip()

        # Parse faculties: "CODE:Name" lines
        faculties = []
        for line in request.POST.get("faculties", "").strip().splitlines():
            line = line.strip()
            if ":" in line:
                code, name = line.split(":", 1)
                faculties.append([code.strip(), name.strip()])

        # Parse candidates: "FacultyCode:FullName" or "FacultyCode:FullName:Position"
        candidates = []
        for line in request.POST.get("candidates", "").strip().splitlines():
            line = line.strip()
            if ":" in line:
                parts = line.split(":", maxsplit=2)
                candidates.append([p.strip() for p in parts])

        # Validate required fields before hitting the API
        if not title or not description or not deadline_at:
            messages.error(request, "Nomi, tavsif va muddati to'ldirilishi shart")
        elif not faculties:
            messages.error(request, "Kamida bitta fakultet kiritilishi kerak")
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
                "created_by": request.user.pk,
                "faculties": faculties,
                "candidates": candidates,
            }
            client = _client()
            try:
                result = client.create_poll(data)
                messages.success(request, f"So'rovnoma yaratildi: {result['poll']['title']}")
                return HttpResponseRedirect(reverse("bot_poll_detail", args=[result["poll"]["id"]]))
            except BotAPIError as e:
                _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/poll_form.html", _ctx(request))


@staff_member_required
def poll_close(request, poll_id: int):
    if request.method == "POST":
        client = _client()
        try:
            client.close_poll(poll_id)
            messages.success(request, "So'rovnoma yopildi")
        except BotAPIError as e:
            _handle_api_error(request, e)
    return HttpResponseRedirect(reverse("bot_poll_detail", args=[poll_id]))


# ─── Export ──────────────────────────────────────────────────────────────────────

@staff_member_required
def export_csv(request, poll_id: int):
    client = _client()
    try:
        data = client.export_csv(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_poll_detail", args=[poll_id]))
    return HttpResponse(data, content_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="poll_{poll_id}.csv"'})


@staff_member_required
def export_pdf(request, poll_id: int):
    client = _client()
    try:
        data = client.export_pdf(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_poll_detail", args=[poll_id]))
    return HttpResponse(data, content_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="poll_{poll_id}_report.pdf"'})


@staff_member_required
def export_json_view(request, poll_id: int):
    client = _client()
    try:
        data = client.export_json(poll_id)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_poll_detail", args=[poll_id]))
    return HttpResponse(data, content_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="poll_{poll_id}.json"'})


ALLOWED_CHART_TYPES = {"trend", "faculty", "hourly", "bar", "pie"}


@staff_member_required
def poll_chart(request, poll_id: int, chart_type: str):
    if chart_type not in ALLOWED_CHART_TYPES:
        return HttpResponse(status=400, content=b"Invalid chart type")
    client = _client()
    try:
        data = client.get_chart(poll_id, chart_type)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_poll_detail", args=[poll_id]))
    return HttpResponse(data, content_type="image/png")


# ─── Admins ──────────────────────────────────────────────────────────────────────

@staff_member_required
def admin_list(request):
    client = _client()
    admin_ids = []
    try:
        admin_ids = client.list_admins()
    except BotAPIError as e:
        _handle_api_error(request, e)

    return TemplateResponse(request, "botproxy/admin_list.html", _ctx(request, {"admin_ids": admin_ids}))


@staff_member_required
def admin_add(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id", "").strip()
        if user_id.isdigit():
            client = _client()
            try:
                client.add_admin(int(user_id), added_by=request.user.pk)
                messages.success(request, f"Admin qo'shildi: {user_id}")
            except BotAPIError as e:
                _handle_api_error(request, e)
        else:
            messages.error(request, "Telegram user ID raqam bo'lishi kerak")
    return HttpResponseRedirect(reverse("bot_admin_list"))


@staff_member_required
def admin_remove(request, user_id: int):
    if request.method == "POST":
        client = _client()
        try:
            client.remove_admin(user_id)
            messages.success(request, f"Admin o'chirildi: {user_id}")
        except BotAPIError as e:
            _handle_api_error(request, e)
    return HttpResponseRedirect(reverse("bot_admin_list"))


# ─── Users ───────────────────────────────────────────────────────────────────────

ALLOWED_SORT_FIELDS = {"name", "registered_at", "total_votes"}


@staff_member_required
def user_stats(request):
    """Users list with pagination, search, sort, and enhanced stats."""
    client = _client()
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

    # ── User detail search by ID ─────────────────────────────────────
    if search_id and search_id.isdigit():
        try:
            user_detail = client.get_user_history(int(search_id))
        except BotAPIError:
            messages.warning(request, f"User {search_id} topilmadi")

    page_range = _build_page_range(page, total_pages)

    return TemplateResponse(request, "botproxy/user_stats.html", _ctx(request, {
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


@staff_member_required
def user_photo_proxy(request, user_id: int):
    """Proxy user profile photo from bot API."""
    client = _client()
    photo_bytes = client.get_user_photo(user_id)
    if not photo_bytes:
        return HttpResponse(status=404)
    return HttpResponse(
        photo_bytes,
        content_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@staff_member_required
def user_growth_chart(request):
    """Proxy user growth chart PNG from bot API."""
    client = _client()
    try:
        data = client.get_user_growth_chart(days=30)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_user_stats"))
    return HttpResponse(data, content_type="image/png")


@staff_member_required
def export_users_csv(request):
    """Download all users as CSV."""
    client = _client()
    try:
        data = client.export_users_csv()
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_user_stats"))
    return HttpResponse(data, content_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="users.csv"'})


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
