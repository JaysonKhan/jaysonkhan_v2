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
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def tg_link(telegram_id, username=None, text=None, css_class=""):
    """Render a Telegram ID as a clickable link.

    Links to https://t.me/{username} if username is provided, else
    renders the plain telegram_id as text.

    Args:
        telegram_id: Telegram user/entity ID (int or str)
        username: Optional Telegram username (without @)
        text: Display text (default: telegram_id)
        css_class: Optional CSS class(es)
    """
    if not telegram_id:
        return ""

    display = text or telegram_id
    if username:
        cls = f' class="{css_class}"' if css_class else ""
        return mark_safe(
            f'<a href="https://t.me/{username}" title="Telegram"'
            f' target="_blank" rel="noopener"{cls}>{display}</a>'
        )
    return str(display)
