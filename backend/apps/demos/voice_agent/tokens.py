"""Short-lived call tokens: the Django page issues one, the relay checks it before opening a paid session.

Format: "<expires_unix>.<nonce>.<hmac>". The HMAC key is derived from Django's SECRET_KEY, so the
relay and the site share no extra secret and the raw SECRET_KEY is never used for anything else.
"""

import hashlib
import hmac
import secrets
import time

TOKEN_TTL_SECONDS = 15 * 60


def _key(secret_key: str) -> bytes:
    return hmac.new(secret_key.encode(), b"jaysonkhan.demos.voice_agent", hashlib.sha256).digest()


def _sign(secret_key: str, payload: str) -> str:
    return hmac.new(_key(secret_key), payload.encode(), hashlib.sha256).hexdigest()[:32]


def issue_token(secret_key: str, now: float | None = None, ttl: int = TOKEN_TTL_SECONDS) -> str:
    payload = f"{int((now or time.time()) + ttl)}.{secrets.token_urlsafe(9)}"
    return f"{payload}.{_sign(secret_key, payload)}"


def verify_token(secret_key: str, token: str, now: float | None = None) -> bool:
    expires, _, rest = token.partition(".")
    nonce, _, signature = rest.partition(".")
    if not (expires.isdigit() and nonce and signature):
        return False
    if not hmac.compare_digest(signature, _sign(secret_key, f"{expires}.{nonce}")):
        return False
    return int(expires) >= (now or time.time())
