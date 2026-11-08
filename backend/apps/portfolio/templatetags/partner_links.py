"""Cross-site UTM for links that leave jaysonkhan.com for a sibling property.

Contract (uzexam/docs/UTM-ATTRIBUTION.md): utm_source=jaysonkhan,
utm_medium=referral, utm_campaign=<placement>. Only sibling hosts are tagged;
client and third-party sites are left untouched, as are URLs that already
carry a utm_source.
"""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django import template

register = template.Library()

PARTNER_HOSTS = ('uzexam.uz', 'edustats.uz', 'vaygo.uz')


def _is_partner_host(netloc: str) -> bool:
    host = (netloc or '').lower().split('@')[-1].split(':')[0]
    if host.startswith('www.'):
        host = host[4:]
    return any(host == h or host.endswith('.' + h) for h in PARTNER_HOSTS)


@register.filter
def partner_utm(url, campaign='project_detail'):
    """Append utm_source=jaysonkhan&utm_medium=referral&utm_campaign=<campaign>
    to a sibling-property URL, preserving its existing query string."""
    if not url:
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not _is_partner_host(parts.netloc):
        return url
    query = parse_qsl(parts.query, keep_blank_values=True)
    if any(key == 'utm_source' for key, _ in query):
        return url
    query += [('utm_source', 'jaysonkhan'), ('utm_medium', 'referral'), ('utm_campaign', campaign)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
