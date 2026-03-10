"""
Telegram authentication verification helpers.
- Login Widget: https://core.telegram.org/widgets/login#checking-authorization
- WebApp initData: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings


def verify_telegram_auth(data: dict) -> bool:
    """
    Verify the hash sent by Telegram Login Widget.
    Returns True if valid and auth_date is within the last 24 hours.
    """
    check_hash = data.get('hash', '')
    if not check_hash:
        return False

    # Build the check string from all fields except 'hash', sorted alphabetically
    fields = {k: v for k, v in data.items() if k != 'hash'}
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(fields.items()))

    # Secret key = SHA-256 of the bot token (NOT base64)
    bot_token = settings.TELEGRAM_BOT_TOKEN
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Compute expected hash
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_hash, check_hash):
        return False

    # Reject auth data older than TELEGRAM_AUTH_MAX_AGE_SECONDS (default 24h)
    max_age = getattr(settings, 'TELEGRAM_AUTH_MAX_AGE_SECONDS', 86400)
    auth_date = int(data.get('auth_date', 0))
    if time.time() - auth_date > max_age:
        return False

    return True


def verify_telegram_webapp_data(init_data_raw: str):
    """
    Verify Telegram WebApp initData string.
    Returns the parsed user dict on success, or None on failure.

    Key difference from Login Widget:
      secret_key = HMAC-SHA256("WebAppData", bot_token)  (not SHA256 of bot_token)
    """
    if not init_data_raw:
        return None

    parsed = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    check_hash = parsed.pop('hash', '')
    if not check_hash:
        return None

    # Build data-check-string: sorted key=value lines
    data_check_string = '\n'.join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    bot_token = settings.TELEGRAM_BOT_TOKEN
    # WebApp secret: HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, check_hash):
        return None

    # Check auth_date freshness
    max_age = getattr(settings, 'TELEGRAM_AUTH_MAX_AGE_SECONDS', 86400)
    auth_date = int(parsed.get('auth_date', 0))
    if time.time() - auth_date > max_age:
        return None

    # Parse user JSON
    user_json = parsed.get('user')
    if not user_json:
        return None

    try:
        user = json.loads(user_json)
    except (json.JSONDecodeError, TypeError):
        return None

    user['auth_date'] = auth_date
    return user
