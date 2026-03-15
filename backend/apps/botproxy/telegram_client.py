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
