"""
Telegram Login Widget verification helper.
Reference: https://core.telegram.org/widgets/login#checking-authorization
"""
import hashlib
import hmac
import time
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
