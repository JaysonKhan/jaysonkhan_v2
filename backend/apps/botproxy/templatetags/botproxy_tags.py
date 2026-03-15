"""Custom template tags / filters for the botproxy app."""
from __future__ import annotations

from urllib.parse import urlparse

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_ALLOWED_SCHEMES = frozenset({"http", "https", ""})


@register.filter(name="safe_url")
def safe_url(value: str) -> str:
    """Return the URL only if it uses an allowed scheme (http/https).

    Blocks javascript:, data:, vbscript:, and other dangerous schemes.
    Returns '#' for unsafe URLs.
    """
    if not value:
        return "#"
    url = str(value).strip()
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return "#"
    return url
