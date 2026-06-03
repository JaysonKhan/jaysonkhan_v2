"""
Global context processor — injects SiteSettings and Telegram session into every template.
"""
from django.conf import settings as django_settings
from django.core.cache import cache

from .services import SiteSettingsService


def site_settings(request):
    """
    Adds ``site_settings``, ``tg_profile`` and ``telegram_bot_username``
    to all template contexts.
    """
    # Telegram session profile (lazy import to avoid circular deps).
    # Cache the lookup by profile id (5 min) so it does not fire an
    # uncached DB query on every page render for authenticated users.
    tg_profile = None
    profile_id = request.session.get('tg_profile_id')
    if profile_id:
        from telegram.models import TelegramEntity
        cache_key = f'tg_profile_{profile_id}'
        tg_profile = cache.get(cache_key)
        if tg_profile is None:
            try:
                tg_profile = TelegramEntity.objects.get(pk=profile_id)
                cache.set(cache_key, tg_profile, 300)
            except TelegramEntity.DoesNotExist:
                request.session.pop('tg_profile_id', None)

    return {
        "site_settings":        SiteSettingsService.get(),
        "tg_profile":           tg_profile,
        "telegram_bot_username": django_settings.TELEGRAM_BOT_USERNAME,
    }
