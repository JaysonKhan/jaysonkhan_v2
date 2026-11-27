"""Rate limits for the public ingestion endpoints, on the Django cache (no new infrastructure).

The client address is never stored: it is turned into an HMAC with a salt that changes every
UTC day (derived from DJANGO_SECRET_KEY), and only that hash appears in cache keys.
Fixed windows: the counter key carries the window number, so `Retry-After` is the time left
in the current window.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

from core.security_middleware import (
    _get_client_ip,  # the one fixed client-IP helper (CLAUDE.md #7)
)
from django.conf import settings
from django.core.cache import cache

HOUR = 3600
DAY = 86400


@dataclass(frozen=True)
class Limit:
    name: str
    max_count: int
    window: int


# Contract "Server obligations" (suggested values).
TELEMETRY_PER_ADDRESS = Limit('tel_addr', 60, HOUR)
RECORDS_PER_INSTALL = Limit('tel_inst', 20_000, DAY)
FEEDBACK_PER_ADDRESS = Limit('fb_addr', 5, HOUR)
BUG_REPORTS_PER_ADDRESS = Limit('bug_addr', 5, HOUR)


def address_hash(request, now: float | None = None) -> str:
    """Salted hash of the client address; the salt rotates every UTC day."""
    now = time.time() if now is None else now
    day = int(now // DAY)
    salt = hmac.new(settings.SECRET_KEY.encode(), f'apptelemetry-ip:{day}'.encode(), hashlib.sha256).digest()
    return hmac.new(salt, _get_client_ip(request).encode(), hashlib.sha256).hexdigest()[:32]


def _key(limit: Limit, subject: str, window_no: int) -> str:
    return f'apptelemetry:{limit.name}:{subject}:{window_no}'


def exceeded(limit: Limit, subject: str, now: float | None = None) -> int | None:
    """Seconds to wait when `subject` has already used up `limit` in this window, else None. Counts nothing."""
    now = time.time() if now is None else now
    window_no = int(now // limit.window)
    if (cache.get(_key(limit, subject, window_no)) or 0) >= limit.max_count:
        return max(1, int((window_no + 1) * limit.window - now))
    return None


def hit(limit: Limit, subject: str, amount: int = 1, now: float | None = None) -> int | None:
    """Count `amount` against `subject`. Returns seconds to wait when over the limit, else None."""
    now = time.time() if now is None else now
    window_no = int(now // limit.window)
    key = _key(limit, subject, window_no)
    # add() sets the TTL on the first hit and is a no-op afterwards; incr() is atomic on Redis
    # (same pattern as contact.spam_protection.is_rate_limited).
    cache.add(key, 0, limit.window + 60)
    try:
        count = cache.incr(key, amount)
    except ValueError:  # evicted between add() and incr()
        cache.set(key, amount, limit.window + 60)
        count = amount
    if count > limit.max_count:
        return max(1, int((window_no + 1) * limit.window - now))
    return None
