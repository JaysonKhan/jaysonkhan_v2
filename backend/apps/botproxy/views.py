"""Django admin views for bot management (polls, analytics, admins, users)."""
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse

from botproxy.client import BotAPIClient, BotAPIError

logger = logging.getLogger(__name__)


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
    try:
        poll_data = client.get_poll(poll_id)
        results = client.get_results(poll_id)
        top = client.get_top(poll_id, limit=10)
    except BotAPIError as e:
        _handle_api_error(request, e)
        return HttpResponseRedirect(reverse("bot_poll_list"))

    return TemplateResponse(request, "botproxy/poll_detail.html", _ctx(request, {
        "poll": poll_data["poll"],
        "faculties": poll_data["faculties"],
        "candidates": poll_data["candidates"],
        "channels": poll_data.get("channels", []),
        "results": results,
        "top": top.get("top", []),
    }))


@staff_member_required
def poll_create(request):
    if request.method == "POST":
        client = _client()
        data = {
            "title": request.POST.get("title", ""),
            "description": request.POST.get("description", ""),
            "deadline_at": request.POST.get("deadline_at", ""),
            "max_votes_per_user": int(request.POST.get("max_votes_per_user", 1)),
            "captcha_enabled": request.POST.get("captcha_enabled") == "on",
            "allow_vote_change": request.POST.get("allow_vote_change") == "on",
            "created_by": request.user.pk,
        }

        # Parse faculties: "CODE:Name" lines
        faculties_raw = request.POST.get("faculties", "").strip()
        data["faculties"] = []
        for line in faculties_raw.splitlines():
            line = line.strip()
            if ":" in line:
                code, name = line.split(":", 1)
                data["faculties"].append([code.strip(), name.strip()])

        # Parse candidates: "FacultyCode:FullName" or "FacultyCode:FullName:Position" lines
        candidates_raw = request.POST.get("candidates", "").strip()
        data["candidates"] = []
        for line in candidates_raw.splitlines():
            line = line.strip()
            if ":" in line:
                parts = line.split(":", maxsplit=2)
                data["candidates"].append([p.strip() for p in parts])

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


@staff_member_required
def poll_chart(request, poll_id: int, chart_type: str):
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

@staff_member_required
def user_stats(request):
    client = _client()
    user_count = 0
    user_detail = None
    search_id = request.GET.get("user_id", "").strip()

    try:
        user_count = client.get_user_count()
    except BotAPIError as e:
        _handle_api_error(request, e)

    if search_id and search_id.isdigit():
        try:
            user_detail = client.get_user_history(int(search_id))
        except BotAPIError:
            messages.warning(request, f"User {search_id} topilmadi")

    return TemplateResponse(request, "botproxy/user_stats.html", _ctx(request, {
        "user_count": user_count,
        "user_detail": user_detail,
        "search_id": search_id,
    }))
