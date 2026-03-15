"""Thread-safe Telethon client manager with StringSession and rate limiting.

Django sync views bilan ishlash uchun background asyncio loop ishlatadi.
Rate limiter Telegram FloodWait xatolarini oldini oladi.

StringSession — session ma'lumotlari PostgreSQL da saqlanadi (SQLite fayl emas).
Bu Gunicorn multi-worker muhitida xavfsiz ishlaydi (database is locked xatolari yo'q).

Usage:
    from telegram.telegram_client import get_telegram_client, run_async

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

# ── Cooldown / Circuit Breaker ──────────────────────────────────────────────
# Agar Telegram connection xato bo'lsa, darhol qayta urinmaslik uchun.
# Bu akkauntni FloodWait / ban dan himoya qiladi.

_last_connection_error: float = 0.0  # monotonic timestamp of last connection failure
_connection_cooldown: float = 30.0   # sekundda — xato bo'lgandan keyin kutish
_last_otp_sent: float = 0.0         # monotonic timestamp of last OTP send
_otp_cooldown: float = 60.0         # sekundda — OTP orasida minimum kutish


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


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_api_config() -> tuple[int, str]:
    """Return (api_id, api_hash).

    Avval DB dan o'qiydi (admin paneldan sozlangan), keyin env fallback.
    Raises RuntimeError if neither source has credentials.
    """
    # 1. DB (admin paneldan sozlangan — restart kerak emas)
    try:
        from telegram.models import TelegramSession

        db_config = TelegramSession.get_api_config()
        if db_config:
            return db_config
    except Exception as e:
        logger.warning("DB dan API config o'qishda xatolik: %s", e)

    # 2. Fallback: environment variables
    api_id = getattr(settings, "TELEGRAM_API_ID", 0)
    api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
    if not api_id or not api_hash:
        raise RuntimeError(
            "TELEGRAM_API_ID va TELEGRAM_API_HASH sozlanmagan. "
            "Session sahifasidan yoki .env faylda sozlang."
        )
    return api_id, api_hash


def _load_session_string() -> str | None:
    """Load session string from PostgreSQL via TelegramSession model.

    IMPORTANT: Must be called from the main (Django) thread, not from
    the background asyncio event loop thread. Django ORM may not have
    a DB connection for the background thread.
    """
    from telegram.models import TelegramSession
    return TelegramSession.get_session_string()


def _make_user_dict(me) -> dict:
    """Create user info dict from Telethon User object."""
    return {
        "id": me.id,
        "first_name": me.first_name or "",
        "last_name": me.last_name or "",
        "username": me.username or "",
        "phone": me.phone or "",
    }


def _format_account_name(me) -> str:
    """Format a Telethon User into a human-readable account name."""
    return f"{me.first_name or ''} @{me.username or me.id}"


def _persist_and_clean_session(result: dict, log_suffix: str = "") -> None:
    """Save session string to PostgreSQL and strip internal keys from result.

    Must be called from the main (Django) thread — uses Django ORM.
    """
    if result.get("ok") and result.get("session_string"):
        from telegram.models import TelegramSession

        TelegramSession.save_session(
            result["session_string"],
            result.get("account_id"),
            result.get("account_name", ""),
        )
        logger.info("Session string PostgreSQL ga saqlandi%s", log_suffix)
    for key in ("session_string", "account_id", "account_name"):
        result.pop(key, None)


# ── Client Manager ───────────────────────────────────────────────────────────


def get_telegram_client():
    """Get or create a connected Telethon client (lazy singleton).

    Thread-safe. Creates a dedicated asyncio event loop in a background
    thread on first call. Reconnects automatically on disconnect.

    Uses StringSession from PostgreSQL — no SQLite file locking issues
    with multiple Gunicorn workers.

    Connection cooldown: agar oldingi ulanish xato bo'lsa, 30 sekund
    kutmasdan qayta urinmaydi (ban oldini olish).

    Raises RuntimeError if API keys or session are not set.
    """
    global _client, _last_connection_error

    # ── Connection cooldown — xato bo'lganda Telegram ni spam qilmaslik ──
    if _last_connection_error > 0:
        elapsed = time.monotonic() - _last_connection_error
        if elapsed < _connection_cooldown:
            remaining = int(_connection_cooldown - elapsed)
            raise RuntimeError(
                f"Telegram ulanish xatosi. {remaining} sekund kutib qayta urining."
            )

    api_id, api_hash = _get_api_config()

    # Load session string from Django thread (ORM-safe) BEFORE acquiring lock
    session_string = _load_session_string()

    with _lock:
        if _client is not None and _client.is_connected():
            return _client

        loop = _ensure_event_loop()

        from telethon import TelegramClient
        from telethon.sessions import StringSession

        if not session_string:
            raise RuntimeError(
                "Telegram session topilmadi. "
                "Admin panel → Telegram Session sahifasidan sessiya yarating."
            )

        _client = TelegramClient(StringSession(session_string), api_id, api_hash)

        try:
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
                    "Admin panel → Telegram Session sahifasidan qayta ulanish."
                )
        except Exception:
            _last_connection_error = time.monotonic()
            _client = None
            raise

        # Muvaffaqiyatli — cooldown ni tozalash
        _last_connection_error = 0.0
        logger.info("Telethon client muvaffaqiyatli ulandi (StringSession)")
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


# ── Telethon Error Handler ────────────────────────────────────────────────────


def _handle_telethon_error(exc: Exception, context: str = "") -> str:
    """Convert Telethon exceptions to user-friendly Uzbek messages.

    Eng muhimi FloodWaitError ni ushlab, kutish vaqtini ko'rsatish —
    foydalanuvchi bilmasa qayta urinadi va ban oladi.
    """
    error_str = str(exc)

    # FloodWaitError — Telegram rate limit. Eng xavfli, chunki
    # qayta urinish banni uzaytiradi.
    try:
        from telethon.errors import FloodWaitError
        if isinstance(exc, FloodWaitError):
            wait_sec = exc.seconds
            if wait_sec >= 3600:
                wait_human = f"{wait_sec // 3600} soat {(wait_sec % 3600) // 60} daqiqa"
            elif wait_sec >= 60:
                wait_human = f"{wait_sec // 60} daqiqa {wait_sec % 60} sekund"
            else:
                wait_human = f"{wait_sec} sekund"
            logger.warning(
                "FloodWaitError (%s): %d sekund kutish kerak",
                context, wait_sec,
            )
            return (
                f"⚠️ Telegram cheklovi: {wait_human} kutish kerak. "
                f"Tez-tez urinish banga olib keladi!"
            )
    except ImportError:
        pass

    # PhoneNumberBannedError / PhoneNumberFloodError
    if "banned" in error_str.lower() or "phone_number_banned" in error_str.lower():
        logger.error("Telefon raqam banlangan (%s): %s", context, error_str)
        return "🚫 Bu telefon raqam Telegram tomonidan banlangan. Boshqa raqam ishlating."

    if "flood" in error_str.lower():
        logger.warning("Flood xatolik (%s): %s", context, error_str)
        return "⚠️ Telegram rate limit. Bir necha daqiqa kutib qayta urinib ko'ring."

    # PhoneCodeInvalidError
    if "phone_code_invalid" in error_str.lower() or "code is invalid" in error_str.lower():
        return "❌ Noto'g'ri kod. Qaytadan kiriting."

    # PhoneCodeExpiredError
    if "phone_code_expired" in error_str.lower() or "code has expired" in error_str.lower():
        return "⏰ Kod muddati o'tgan. Yangi kod so'rang."

    # PasswordHashInvalidError
    if "password" in error_str.lower() and "invalid" in error_str.lower():
        return "❌ Noto'g'ri parol."

    # ApiIdInvalidError
    if "api_id" in error_str.lower() and "invalid" in error_str.lower():
        return "🚫 API ID noto'g'ri. my.telegram.org dan tekshiring."

    # AuthKeyError — session buzilgan
    if "auth" in error_str.lower() and "key" in error_str.lower():
        logger.error("AuthKey xatolik (%s): %s", context, error_str)
        return "🔑 Session buzilgan. Qaytadan ulanish kerak."

    # Generic
    logger.exception("%s da xatolik: %s", context, exc)
    return f"Xatolik: {error_str}"


# ── Session Setup Helpers ─────────────────────────────────────────────────────

# Temporary client for session setup (phone → OTP → sign in flow)
_setup_client = None
_setup_phone_hash: str | None = None


def check_session_status() -> dict:
    """Check current Telegram session status.

    Uses StringSession from PostgreSQL. Each worker can independently
    load the session without file locking.

    Returns dict with:
        configured: bool — API keys sozlanganmi
        authorized: bool — session avtorizatsiya qilinganmi
        user: dict | None — {id, first_name, last_name, username, phone}
        api_id: int | None — hozirgi API ID (UI uchun)
        api_hash_set: bool — API Hash sozlanganmi
    """
    try:
        api_id, api_hash = _get_api_config()
    except RuntimeError:
        # DB da ham env da ham yo'q — faqat DB config borligini tekshiramiz
        from telegram.models import TelegramSession

        db_config = TelegramSession.get_api_config()
        return {
            "configured": False,
            "authorized": False,
            "user": None,
            "api_id": db_config[0] if db_config else None,
            "api_hash_set": bool(db_config),
        }

    # Load session string from Django thread (ORM-safe) BEFORE async
    session_string = _load_session_string()

    loop = _ensure_event_loop()

    async def _check():
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        # 1. Try existing singleton client first (same worker, already connected)
        if _client is not None:
            try:
                if not _client.is_connected():
                    await _client.connect()
                if await _client.is_user_authorized():
                    me = await _client.get_me()
                    return {
                        "configured": True,
                        "authorized": True,
                        "user": _make_user_dict(me),
                    }
            except Exception as e:
                logger.warning("Singleton client tekshirishda xatolik: %s", e)

        # 2. Check if session string exists
        if not session_string:
            return {"configured": True, "authorized": False, "user": None}

        # 3. Create temporary client with StringSession (no file locking!)
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                return {
                    "configured": True,
                    "authorized": True,
                    "user": _make_user_dict(me),
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
    result = future.result(timeout=30)

    # API config info ni qo'shish (UI uchun)
    result["api_id"] = api_id
    result["api_hash_set"] = bool(api_hash)
    return result


def setup_send_code(phone: str) -> dict:
    """Send OTP code to phone number for session setup.

    Uses empty StringSession (new session, no file needed).
    OTP orasida minimum 60 sekund kutish — spam oldini olish.

    Returns dict with:
        ok: bool
        phone_code_hash: str (Telethon internal)
        error: str | None
    """
    global _setup_client, _setup_phone_hash, _last_otp_sent

    # ── OTP rate limit — tez-tez OTP so'rash akkauntni banga olib keladi ──
    now = time.monotonic()
    elapsed_since_otp = now - _last_otp_sent
    if _last_otp_sent > 0 and elapsed_since_otp < _otp_cooldown:
        remaining = int(_otp_cooldown - elapsed_since_otp)
        return {
            "ok": False,
            "error": f"OTP tez-tez so'rash mumkin emas. {remaining} sekund kuting.",
        }

    api_id, api_hash = _get_api_config()
    loop = _ensure_event_loop()

    async def _send():
        global _setup_client, _setup_phone_hash
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        # Close existing setup client if any
        if _setup_client:
            try:
                await _setup_client.disconnect()
            except Exception:
                pass

        # Empty StringSession — brand new session, no files
        _setup_client = TelegramClient(StringSession(), api_id, api_hash)
        await _setup_client.connect()

        result = await _setup_client.send_code_request(phone)
        _setup_phone_hash = result.phone_code_hash
        return {"ok": True, "phone_code_hash": result.phone_code_hash}

    try:
        future = asyncio.run_coroutine_threadsafe(_send(), loop)
        result = future.result(timeout=30)
        if result.get("ok"):
            _last_otp_sent = time.monotonic()
        return result
    except Exception as e:
        error_msg = _handle_telethon_error(e, "OTP yuborish")
        return {"ok": False, "error": error_msg}


def setup_verify_code(phone: str, code: str) -> dict:
    """Verify OTP code and sign in.

    On success, exports StringSession and saves to PostgreSQL.

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
            return {"ok": False, "needs_2fa": True, "user": None, "session_string": None}
        except Exception as e:
            return {"ok": False, "needs_2fa": False, "error": str(e), "user": None, "session_string": None}

        me = await _setup_client.get_me()
        user_dict = _make_user_dict(me)

        # Export session string (will be saved to DB in sync context)
        session_string = _setup_client.session.save()
        account_name = _format_account_name(me)

        # Update the main singleton client
        with _lock:
            _client = _setup_client

        return {
            "ok": True,
            "needs_2fa": False,
            "user": user_dict,
            "session_string": session_string,
            "account_id": me.id,
            "account_name": account_name,
        }

    try:
        future = asyncio.run_coroutine_threadsafe(_verify(), loop)
        result = future.result(timeout=30)
        _persist_and_clean_session(result)
        return result
    except Exception as e:
        error_msg = _handle_telethon_error(e, "OTP tekshirish")
        return {"ok": False, "needs_2fa": False, "error": error_msg}


def setup_verify_2fa(password: str) -> dict:
    """Verify 2FA password and complete sign in.

    On success, exports StringSession and saves to PostgreSQL.

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
            return {"ok": False, "error": str(e), "user": None, "session_string": None}

        me = await _setup_client.get_me()
        user_dict = _make_user_dict(me)

        # Export session string (will be saved to DB in sync context)
        session_string = _setup_client.session.save()
        account_name = _format_account_name(me)

        # Update the main singleton client
        with _lock:
            _client = _setup_client

        return {
            "ok": True,
            "user": user_dict,
            "session_string": session_string,
            "account_id": me.id,
            "account_name": account_name,
        }

    try:
        future = asyncio.run_coroutine_threadsafe(_verify_2fa(), loop)
        result = future.result(timeout=30)
        _persist_and_clean_session(result, " (2FA)")
        return result
    except Exception as e:
        error_msg = _handle_telethon_error(e, "2FA tekshirish")
        return {"ok": False, "error": error_msg}


def disconnect_session() -> dict:
    """Disconnect and invalidate the current session.

    Clears StringSession from PostgreSQL and disconnects all clients.

    Returns dict with ok: bool, error: str | None
    """
    global _client, _setup_client

    loop = _ensure_event_loop()

    async def _disconnect():
        global _client, _setup_client

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

        return {"ok": True}

    try:
        future = asyncio.run_coroutine_threadsafe(_disconnect(), loop)
        result = future.result(timeout=30)

        # Clear session from PostgreSQL in sync context (Django ORM-safe)
        from telegram.models import TelegramSession
        TelegramSession.clear_session()
        logger.info("Session PostgreSQL dan o'chirildi")

        # Also clean up legacy session files if they exist
        import os
        session_path = getattr(settings, "TELEGRAM_SESSION_PATH", "")
        if session_path:
            for ext in ("", ".session"):
                path = f"{session_path}{ext}"
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info("Eski session fayl o'chirildi: %s", path)
                    except Exception:
                        pass

        return result
    except Exception as e:
        logger.exception("Session uzishda xatolik: %s", e)
        return {"ok": False, "error": str(e)}
