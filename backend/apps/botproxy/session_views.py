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
        logger.exception("Telegram session status check failed")
        return JsonResponse({
            "configured": True, "authorized": False,
            "user": None, "error": "Sessiya holatini tekshirishda xatolik yuz berdi",
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


@staff_member_required
@require_POST
def telegram_session_save_config(request):
    """AJAX POST: save API ID and API Hash.

    Admin paneldan API credentials ni sozlash.
    Saqlangandan keyin mavjud client ni uzadi (yangi credentials bilan ulanish uchun).
    """
    from telegram.models import TelegramSession
    from telegram.telegram_client import shutdown_client

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ok": False, "error": "Noto'g'ri so'rov"}, status=400)

    try:
        api_id = int(body.get("api_id", 0))
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "API ID raqam bo'lishi kerak"}, status=400)

    api_hash = body.get("api_hash", "").strip()

    if not api_id or not api_hash:
        return JsonResponse({"ok": False, "error": "API ID va API Hash kiritilmagan"}, status=400)

    if len(api_hash) < 16:
        return JsonResponse({"ok": False, "error": "API Hash kamida 16 belgi bo'lishi kerak"}, status=400)

    TelegramSession.save_api_config(api_id, api_hash)

    # Mavjud client ni uzish (yangi credentials bilan qayta ulanish uchun)
    shutdown_client()
    logger.info("API config saqlandi: api_id=%s", api_id)

    return JsonResponse({"ok": True})
