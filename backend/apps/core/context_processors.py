"""
Global context processor for site-wide settings.
Makes SiteSettings available to all templates.
"""
from .models import SiteSettings


def site_settings(request):
    """
    Inject SiteSettings into template context.
    Accessible as {{ site_settings }} in all templates.
    """
    try:
        settings = SiteSettings.load()
    except Exception:
        # Fallback if DB is unavailable (e.g., migrations running)
        settings = None

    return {
        'site_settings': settings,
    }
