"""
Global context processor — injects SiteSettings and Telegram session into every template.
"""
from django.conf import settings as django_settings
from .services import SiteSettingsService


def site_settings(request):
    """
    Adds ``site_settings``, ``tg_profile`` and ``telegram_bot_username``
    to all template contexts.
    """
    # Telegram session profile (lazy import to avoid circular deps)
    tg_profile = None
    profile_id = request.session.get('tg_profile_id')
    if profile_id:
        try:
            from interactions.models import TelegramProfile
            tg_profile = TelegramProfile.objects.get(pk=profile_id)
        except Exception:
            request.session.pop('tg_profile_id', None)

    return {
        "site_settings":        SiteSettingsService.get(),
        "tg_profile":           tg_profile,
        "telegram_bot_username": django_settings.TELEGRAM_BOT_USERNAME,
    }
