"""Telegram MTProto session management views.

Web UI for setting up and managing the Telethon session:
  - Check session status
  - Send OTP to phone number
  - Verify OTP code
  - Verify 2FA password (if enabled)
  - Disconnect session

All views are staff-only and use AJAX for multi-step wizard flow.
"""
from __future__ import annotations

import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _ctx(request, extra: dict | None = None) -> dict:
    """Base context for session views (includes Unfold admin context)."""
    from django.contrib import admin

    ctx = admin.site.each_context(request)
    ctx["is_osint"] = True
    if extra:
        ctx.update(extra)
    return ctx


@staff_member_required
def telegram_session_page(request):
    """Main session management page."""
    return TemplateResponse(
        request,
        "botproxy/telegram_session.html",
        _ctx(request),
    )


@staff_member_required
def telegram_session_status(request):
    """AJAX: check current session status."""
    from telegram.telegram_client import check_session_status

    try:
        status = check_session_status()
    except Exception as e:
        # configured=True because API keys exist, but connection failed
        return JsonResponse({
            "configured": True, "authorized": False,
            "user": None, "error": str(e),
        })

    return JsonResponse(status)


@staff_member_required
@require_POST
def telegram_session_send_code(request):
    """AJAX POST: send OTP code to phone number."""
    from telegram.telegram_client import setup_send_code

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ok": False, "error": "Noto'g'ri so'rov"}, status=400)

    phone = body.get("phone", "").strip()
    if not phone:
        return JsonResponse({"ok": False, "error": "Telefon raqam kiritilmagan"}, status=400)

    result = setup_send_code(phone)
    return JsonResponse(result)


@staff_member_required
@require_POST
def telegram_session_verify(request):
    """AJAX POST: verify OTP code."""
    from telegram.telegram_client import setup_verify_code

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ok": False, "error": "Noto'g'ri so'rov"}, status=400)

    phone = body.get("phone", "").strip()
    code = body.get("code", "").strip()

    if not phone or not code:
        return JsonResponse({"ok": False, "error": "Telefon va kod kiritilmagan"}, status=400)

    result = setup_verify_code(phone, code)
    return JsonResponse(result)


@staff_member_required
@require_POST
def telegram_session_2fa(request):
    """AJAX POST: verify 2FA password."""
    from telegram.telegram_client import setup_verify_2fa

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ok": False, "error": "Noto'g'ri so'rov"}, status=400)

    password = body.get("password", "").strip()
    if not password:
        return JsonResponse({"ok": False, "error": "Parol kiritilmagan"}, status=400)

    result = setup_verify_2fa(password)
    return JsonResponse(result)


@staff_member_required
@require_POST
def telegram_session_disconnect(request):
    """AJAX POST: disconnect and invalidate session."""
    from telegram.telegram_client import disconnect_session

    result = disconnect_session()
    return JsonResponse(result)
