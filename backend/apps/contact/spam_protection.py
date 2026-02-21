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
    current = cache.get(key, 0)

    if current >= RATE_LIMIT_MAX_SUBMISSIONS:
        logger.warning("Rate-limit hit for IP %s (%d/%d)", ip, current, RATE_LIMIT_MAX_SUBMISSIONS)
        return True

    # Increment counter; set TTL on first hit
    cache.set(key, current + 1, RATE_LIMIT_WINDOW_SECONDS)
    return False


def _get_client_ip(request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind reverse proxies."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')
