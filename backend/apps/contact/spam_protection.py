"""
Contact form spam protection utilities.

1. Honeypot: hidden field that bots fill in, humans don't.
2. Rate limiting: per-IP throttle using Django's cache framework.
3. Contact-field validation: the value must be a real email or @handle.
4. Content signature: link blasts and known bulk-spam phrases.
"""
import logging
import re

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

logger = logging.getLogger(__name__)

# ── Rate-limit settings ──────────────────────────────────────────────────────
RATE_LIMIT_KEY_PREFIX = "contact_rate_"
RATE_LIMIT_MAX_SUBMISSIONS = 3      # max submissions per window
RATE_LIMIT_WINDOW_SECONDS = 600     # 10-minute window


def is_honeypot_filled(request) -> bool:
    """
    Return True if the honeypot field was filled → likely a bot.

    The field is named 'referral_code', not the usual 'website'/'url' bait:
    bulk form-spam software (XRumer & friends) carries a skip-list of the
    common bait names, so the classic ones catch nothing.
    """
    value = request.POST.get('referral_code', '')
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


# ── Contact-field / content checks ───────────────────────────────────────────
# The form offers one field for either contact route ("@username / email"), so
# EmailField validation alone would reject legitimate Telegram handles.
TELEGRAM_HANDLE_RE = re.compile(r'^@[A-Za-z0-9_]{4,32}$')
URL_RE = re.compile(r'https?://', re.IGNORECASE)
MAX_URLS = 2

# Phrases taken from the 2026-06..08 bulk-spam campaigns. Kept deliberately
# short and unambiguous: a false positive here silently drops a real lead.
SPAM_PHRASES = (
    'jackpot',
    'promo code',
    'per day or more',
    'crypto-powered',
    'collect cryptocurrency',
    'followers per month',
    'instagram growth',
    'contact forms at mass',
)


def is_valid_contact(value: str) -> bool:
    """Return True if value is a real email address or a Telegram handle."""
    if TELEGRAM_HANDLE_RE.match(value):
        return True
    try:
        validate_email(value)
    except ValidationError:
        return False
    return True


def is_spam_content(request, message: str) -> bool:
    """Return True if the message body matches a known bulk-spam signature."""
    if len(URL_RE.findall(message)) > MAX_URLS:
        logger.warning("Link-blast spam from IP %s (%d urls)",
                       _get_client_ip(request), len(URL_RE.findall(message)))
        return True

    lowered = message.lower()
    hit = next((p for p in SPAM_PHRASES if p in lowered), None)
    if hit:
        logger.warning("Spam phrase %r from IP %s", hit, _get_client_ip(request))
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
