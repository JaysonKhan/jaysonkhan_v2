"""
Contact form spam protection utilities.

1. Honeypot: hidden field that bots fill in, humans don't.
2. Rate limiting: per-IP throttle using Django's cache framework.
"""
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

# ── Rate-limit settings ──────────────────────────────────────────────────────
RATE_LIMIT_KEY_PREFIX = "contact_rate_"
RATE_LIMIT_MAX_SUBMISSIONS = 3      # max submissions per window
RATE_LIMIT_WINDOW_SECONDS = 600     # 10-minute window


def is_honeypot_filled(request) -> bool:
    """
    Return True if the honeypot field was filled → likely a bot.
    The hidden field is named 'website' (common bait name).
    """
    value = request.POST.get('website', '')
    if value:
        logger.warning(
            "Honeypot triggered from IP %s (value=%r)",
            _get_client_ip(request), value,
        )
        return True
    return False


def is_rate_limited(request) -> bool:
    """
    Return True if the client has exceeded the rate limit for contact submissions.
    Uses Django cache (LocMemCache/Redis) with per-IP keys.
    """
    ip = _get_client_ip(request)
    key = f"{RATE_LIMIT_KEY_PREFIX}{ip}"

    # Atomic increment: cache.add is a no-op if the key already exists (and sets
    # the TTL on the first hit), then cache.incr is atomic on Redis. Doing
    # get()+set() as two calls races under concurrent Gunicorn workers and lets
    # a burst slip past the limit. The add() also guards LocMemCache.incr, which
    # raises ValueError on a missing key.
    cache.add(key, 0, RATE_LIMIT_WINDOW_SECONDS)
    count = cache.incr(key)

    if count > RATE_LIMIT_MAX_SUBMISSIONS:
        logger.warning("Rate-limit hit for IP %s (%d/%d)", ip, count, RATE_LIMIT_MAX_SUBMISSIONS)
        return True
    return False


def _get_client_ip(request) -> str:
    """
    Return the real client IP.

    Nginx (single trusted proxy) sets X-Real-IP to the real client IP
    ($remote_addr) and OVERWRITES any client value, so it is unspoofable.
    REMOTE_ADDR is empty here because Gunicorn binds a unix socket (no TCP
    peer) — reading it alone made every submission share one empty-IP
    rate-limit bucket. X-Forwarded-For is NOT trusted (Nginx *appends* to it,
    so its leftmost entry is attacker-controlled).
    """
    return (request.META.get('HTTP_X_REAL_IP')
            or request.META.get('REMOTE_ADDR')
            or '0.0.0.0')
