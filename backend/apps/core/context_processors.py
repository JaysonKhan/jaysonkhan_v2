"""
Global context processor — injects SiteSettings into every template.
Uses SiteSettingsService so the result is always served from cache.
"""
from .services import SiteSettingsService


def site_settings(request):
    """
    Adds ``site_settings`` to all template contexts.
    Safe: SiteSettingsService.get() never raises — returns defaults on failure.
    """
    return {
        "site_settings": SiteSettingsService.get(),
    }
