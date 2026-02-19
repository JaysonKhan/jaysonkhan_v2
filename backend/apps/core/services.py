"""
SiteSettings service layer.

Caching strategy: Django's per-process in-memory cache (LocMemCache).
TTL: 5 minutes. Invalidated on every admin save via post_save signal.
No Redis required — upgrade path: swap CACHES backend in settings, zero code change.
"""
import logging
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SiteSettings

logger = logging.getLogger(__name__)

CACHE_KEY = "site_settings_singleton"
CACHE_TTL = 60 * 5  # 5 minutes


class SiteSettingsService:
    """
    Read-only service for retrieving SiteSettings with transparent caching.
    Write path goes through Django admin → post_save signal invalidates cache.
    """

    @staticmethod
    def get() -> SiteSettings:
        """
        Return cached SiteSettings instance.
        On cache miss: fetches from DB, populates cache, returns instance.
        On DB error: returns a fresh in-memory instance with defaults (safe fallback).
        """
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached

        try:
            obj = SiteSettings.load()
            cache.set(CACHE_KEY, obj, CACHE_TTL)
            return obj
        except Exception as exc:
            logger.warning("SiteSettings DB fetch failed, using defaults: %s", exc)
            return SiteSettings()  # in-memory instance, all field defaults apply

    @staticmethod
    def invalidate() -> None:
        """Bust the cache — call after any write to SiteSettings."""
        cache.delete(CACHE_KEY)
        logger.debug("SiteSettings cache invalidated")


# ── Signal: auto-invalidate on admin save ────────────────────────────────────

@receiver(post_save, sender=SiteSettings)
def _invalidate_on_save(sender, instance, **kwargs):
    """Automatically bust cache whenever SiteSettings is saved."""
    SiteSettingsService.invalidate()
