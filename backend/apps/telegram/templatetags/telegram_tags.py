"""Template tags for Telegram entity links.

Usage:
    {% load telegram_tags %}

    {# Simple — shows ID as link #}
    {% tg_link 123456789 %}

    {# With custom display text #}
    {% tg_link user_id text="John Doe" %}

    {# With CSS class #}
    {% tg_link user_id css_class="text-blue-400 hover:underline" %}
"""
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def tg_link(telegram_id, text=None, css_class=""):
    """Render a Telegram ID as a clickable link to the OSINT profile.

    Args:
        telegram_id: Telegram user/entity ID (int or str)
        text: Display text (default: telegram_id)
        css_class: Optional CSS class(es)
    """
    if not telegram_id:
        return ""

    try:
        url = reverse("osint_profile", kwargs={"user_id": int(telegram_id)})
    except Exception:
        return str(telegram_id)

    display = text or telegram_id
    cls = f' class="{css_class}"' if css_class else ""
    return mark_safe(
        f'<a href="{url}" title="OSINT profil"{cls}>{display}</a>'
    )
