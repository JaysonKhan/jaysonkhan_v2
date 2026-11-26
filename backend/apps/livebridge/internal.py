"""The gateway's calls into the site: authorize an access token, report usage.

They exist only for a request that reached Gunicorn's unix socket directly (no X-Real-IP or
X-Forwarded-For — the public web server always sets them) and is signed with the shared
`LIVEBRIDGE_GATEWAY_SECRET` over `"{timestamp}." + body`, within 60 seconds of our clock. Anything else
gets the same 404 as a route that does not exist. The gateway sends `Host: jaysonkhan.com` and
`X-Forwarded-Proto: https` (otherwise the HTTPS redirect answers 301).
"""
from __future__ import annotations

import hashlib
import hmac
import time

from django.conf import settings

SIGNATURE_HEADER = 'HTTP_X_LIVEBRIDGE_SIGNATURE'
TIMESTAMP_HEADER = 'HTTP_X_LIVEBRIDGE_TIMESTAMP'
CLOCK_SKEW = 60  # seconds


def sign(body: bytes, timestamp: int, secret: str) -> str:
    return hmac.new(secret.encode(), f'{timestamp}.'.encode() + body, hashlib.sha256).hexdigest()


def is_internal_request(request, now: float | None = None) -> bool:
    secret = settings.LIVEBRIDGE_GATEWAY_SECRET
    if not secret:
        return False
    meta = request.META
    if meta.get('HTTP_X_REAL_IP') or meta.get('HTTP_X_FORWARDED_FOR'):
        return False
    try:
        timestamp = int(meta.get(TIMESTAMP_HEADER, ''))
    except ValueError:
        return False
    if abs((time.time() if now is None else now) - timestamp) > CLOCK_SKEW:
        return False
    return hmac.compare_digest(sign(request.body, timestamp, secret), meta.get(SIGNATURE_HEADER, ''))
