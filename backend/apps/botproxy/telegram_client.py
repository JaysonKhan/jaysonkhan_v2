"""Thread-safe Telethon client manager with lazy singleton and rate limiting.

Django sync views bilan ishlash uchun background asyncio loop ishlatadi.
Rate limiter Telegram FloodWait xatolarini oldini oladi.

Usage:
    from botproxy.telegram_client import get_telegram_client, run_async

    client = get_telegram_client()
    result = run_async(client.download_profile_photo(entity, file=bytes))
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque

from django.conf import settings

logger = logging.getLogger(__name__)

_client = None
_lock = threading.Lock()
_loop = None
_loop_thread = None


# ── Rate Limiter ─────────────────────────────────────────────────────────────


class TelegramRateLimiter:
    """Sliding window rate limiter for Telegram API calls."""

    def __init__(self, max_per_minute: int = 15):
        self.max_per_minute = max_per_minute
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """Block until a slot is available. Returns False if timed out."""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                # Remove timestamps older than 60 seconds
                while self._timestamps and self._timestamps[0] < now - 60:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.max_per_minute:
                    self._timestamps.append(now)
                    return True
            if time.monotonic() > deadline:
                return False
            # Wait a bit before retrying
            with self._lock:
                if self._timestamps:
                    wait = max(0.1, min(60 - (time.monotonic() - self._timestamps[0]), 1.0))
                else:
                    wait = 0.1
            time.sleep(wait)


_rate_limiter: TelegramRateLimiter | None = None


def get_rate_limiter() -> TelegramRateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        max_rpm = getattr(settings, "OSINT_PHOTO_MAX_REQUESTS_PER_MIN", 15)
        _rate_limiter = TelegramRateLimiter(max_per_minute=max_rpm)
    return _rate_limiter


# ── Event Loop ───────────────────────────────────────────────────────────────


def _ensure_event_loop() -> asyncio.AbstractEventLoop:
    """Create a dedicated event loop running in a background daemon thread."""
    global _loop, _loop_thread
    if _loop is not None and _loop.is_running():
        return _loop

    _loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    _loop_thread = threading.Thread(target=run_loop, daemon=True, name="telethon-loop")
    _loop_thread.start()
    return _loop


# ── Client Manager ───────────────────────────────────────────────────────────


def get_telegram_client():
    """Get or create a connected Telethon client (lazy singleton).

    Thread-safe. Creates a dedicated asyncio event loop in a background
    thread on first call. Reconnects automatically on disconnect.

    Raises RuntimeError if TELEGRAM_API_ID or TELEGRAM_API_HASH are not set,
    or if the session is not authorized (run setup_telegram_session first).
    """
    global _client

    api_id = getattr(settings, "TELEGRAM_API_ID", 0)
    api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
    session_path = getattr(settings, "TELEGRAM_SESSION_PATH", "")

    if not api_id or not api_hash:
        raise RuntimeError(
            "TELEGRAM_API_ID va TELEGRAM_API_HASH sozlanmagan. "
            "https://my.telegram.org/apps dan oling."
        )

    with _lock:
        if _client is not None and _client.is_connected():
            return _client

        loop = _ensure_event_loop()

        from telethon import TelegramClient

        _client = TelegramClient(session_path, api_id, api_hash)

        # Connect in the background loop
        future = asyncio.run_coroutine_threadsafe(_client.connect(), loop)
        future.result(timeout=30)

        # Check authorization
        auth_future = asyncio.run_coroutine_threadsafe(
            _client.is_user_authorized(), loop
        )
        if not auth_future.result(timeout=10):
            raise RuntimeError(
                "Telegram session avtorizatsiya qilinmagan. "
                "Ishga tushiring: python manage.py setup_telegram_session"
            )

        logger.info("Telethon client muvaffaqiyatli ulandi")
        return _client


def run_async(coro):
    """Run an async coroutine from synchronous Django code.

    Uses the background event loop that the Telethon client runs on.
    Thread-safe.
    """
    loop = _ensure_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=60)


def shutdown_client():
    """Gracefully disconnect the Telethon client."""
    global _client, _loop
    with _lock:
        if _client and _client.is_connected():
            try:
                if _loop and _loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        _client.disconnect(), _loop
                    )
                    future.result(timeout=10)
            except Exception:
                logger.exception("Telethon client ni uzishda xatolik")
            _client = None


# ── Session Setup Helpers ─────────────────────────────────────────────────────

# Temporary client for session setup (phone → OTP → sign in flow)
_setup_client = None
_setup_phone_hash: str | None = None


def _get_api_config() -> tuple[int, str, str]:
    """Return (api_id, api_hash, session_path). Raises RuntimeError if missing."""
    api_id = getattr(settings, "TELEGRAM_API_ID", 0)
    api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
    session_path = getattr(settings, "TELEGRAM_SESSION_PATH", "")
    if not api_id or not api_hash:
        raise RuntimeError(
            "TELEGRAM_API_ID va TELEGRAM_API_HASH sozlanmagan. "
            "https://my.telegram.org/apps dan oling."
        )
    return api_id, api_hash, session_path


def check_session_status() -> dict:
    """Check current Telegram session status.

    First tries the existing singleton client (_client), then falls back to
    creating a temporary connection. This avoids SQLite session file conflicts.

    Returns dict with:
        configured: bool — API keys sozlanganmi
        authorized: bool — session avtorizatsiya qilinganmi
        user: dict | None — {id, first_name, last_name, username, phone}
    """
    api_id = getattr(settings, "TELEGRAM_API_ID", 0)
    api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
    session_path = getattr(settings, "TELEGRAM_SESSION_PATH", "")

    if not api_id or not api_hash:
        return {"configured": False, "authorized": False, "user": None}

    loop = _ensure_event_loop()

    async def _check():
        from telethon import TelegramClient

        # 1. Try existing singleton client first
        if _client is not None:
            try:
                if not _client.is_connected():
                    await _client.connect()
                if await _client.is_user_authorized():
                    me = await _client.get_me()
                    return {
                        "configured": True,
                        "authorized": True,
                        "user": {
                            "id": me.id,
                            "first_name": me.first_name or "",
                            "last_name": me.last_name or "",
                            "username": me.username or "",
                            "phone": me.phone or "",
                        },
                    }
            except Exception as e:
                logger.warning("Singleton client tekshirishda xatolik: %s", e)

        # 2. Try with a fresh temporary client
        client = TelegramClient(session_path, api_id, api_hash)
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                return {
                    "configured": True,
                    "authorized": True,
                    "user": {
                        "id": me.id,
                        "first_name": me.first_name or "",
                        "last_name": me.last_name or "",
                        "username": me.username or "",
                        "phone": me.phone or "",
                    },
                }
            return {"configured": True, "authorized": False, "user": None}
        except Exception as e:
            logger.exception("Session status tekshirishda xatolik: %s", e)
            return {"configured": True, "authorized": False, "user": None, "error": str(e)}
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    future = asyncio.run_coroutine_threadsafe(_check(), loop)
    return future.result(timeout=30)


def setup_send_code(phone: str) -> dict:
    """Send OTP code to phone number for session setup.

    Returns dict with:
        ok: bool
        phone_code_hash: str (Telethon internal)
        error: str | None
    """
    global _setup_client, _setup_phone_hash

    api_id, api_hash, session_path = _get_api_config()
    loop = _ensure_event_loop()

    async def _send():
        global _setup_client, _setup_phone_hash
        from telethon import TelegramClient

        # Close existing setup client if any
        if _setup_client:
            try:
                await _setup_client.disconnect()
            except Exception:
                pass

        _setup_client = TelegramClient(session_path, api_id, api_hash)
        await _setup_client.connect()

        result = await _setup_client.send_code_request(phone)
        _setup_phone_hash = result.phone_code_hash
        return {"ok": True, "phone_code_hash": result.phone_code_hash}

    try:
        future = asyncio.run_coroutine_threadsafe(_send(), loop)
        return future.result(timeout=30)
    except Exception as e:
        logger.exception("OTP yuborishda xatolik: %s", e)
        return {"ok": False, "error": str(e)}


def setup_verify_code(phone: str, code: str) -> dict:
    """Verify OTP code and sign in.

    Returns dict with:
        ok: bool
        needs_2fa: bool — True if 2FA password required
        user: dict | None — user info if successful
        error: str | None
    """
    global _setup_client, _setup_phone_hash, _client

    if not _setup_client:
        return {"ok": False, "error": "Avval telefon raqam kiriting", "needs_2fa": False}

    loop = _ensure_event_loop()

    async def _verify():
        global _client
        from telethon.errors import SessionPasswordNeededError

        try:
            await _setup_client.sign_in(phone, code, phone_code_hash=_setup_phone_hash)
        except SessionPasswordNeededError:
            return {"ok": False, "needs_2fa": True, "user": None}
        except Exception as e:
            return {"ok": False, "needs_2fa": False, "error": str(e), "user": None}

        me = await _setup_client.get_me()

        # Update the main singleton client
        with _lock:
            _client = _setup_client

        return {
            "ok": True,
            "needs_2fa": False,
            "user": {
                "id": me.id,
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
                "phone": me.phone or "",
            },
        }

    try:
        future = asyncio.run_coroutine_threadsafe(_verify(), loop)
        return future.result(timeout=30)
    except Exception as e:
        logger.exception("OTP tekshirishda xatolik: %s", e)
        return {"ok": False, "needs_2fa": False, "error": str(e)}


def setup_verify_2fa(password: str) -> dict:
    """Verify 2FA password and complete sign in.

    Returns dict with:
        ok: bool
        user: dict | None
        error: str | None
    """
    global _setup_client, _client

    if not _setup_client:
        return {"ok": False, "error": "Session yo'q — qaytadan boshlang"}

    loop = _ensure_event_loop()

    async def _verify_2fa():
        global _client
        try:
            await _setup_client.sign_in(password=password)
        except Exception as e:
            return {"ok": False, "error": str(e), "user": None}

        me = await _setup_client.get_me()

        # Update the main singleton client
        with _lock:
            _client = _setup_client

        return {
            "ok": True,
            "user": {
                "id": me.id,
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
                "phone": me.phone or "",
            },
        }

    try:
        future = asyncio.run_coroutine_threadsafe(_verify_2fa(), loop)
        return future.result(timeout=30)
    except Exception as e:
        logger.exception("2FA tekshirishda xatolik: %s", e)
        return {"ok": False, "error": str(e)}


def disconnect_session() -> dict:
    """Disconnect and invalidate the current session.

    Returns dict with ok: bool, error: str | None
    """
    global _client, _setup_client

    api_id = getattr(settings, "TELEGRAM_API_ID", 0)
    api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
    session_path = getattr(settings, "TELEGRAM_SESSION_PATH", "")

    loop = _ensure_event_loop()

    async def _disconnect():
        global _client, _setup_client
        from telethon import TelegramClient

        # Disconnect any existing clients
        for c in (_client, _setup_client):
            if c:
                try:
                    if c.is_connected():
                        await c.log_out()
                except Exception:
                    pass
        _client = None
        _setup_client = None

        # Remove session files
        import os
        for ext in ("", ".session"):
            path = f"{session_path}{ext}"
            if os.path.exists(path):
                os.remove(path)

        return {"ok": True}

    try:
        future = asyncio.run_coroutine_threadsafe(_disconnect(), loop)
        return future.result(timeout=30)
    except Exception as e:
        logger.exception("Session uzishda xatolik: %s", e)
        return {"ok": False, "error": str(e)}
