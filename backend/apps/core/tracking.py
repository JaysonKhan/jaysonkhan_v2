"""
Visitor attribution — first-touch source tracking.

`classify_source()` maps an inbound request (UTM params + Referer header) to a
canonical traffic source, and `VisitorTrackingMiddleware` records ONE PageView
row per unique visitor (cookie + real-IP dedup) on first touch, capturing the
landing page, referrer, UTM tags and classified source. Returning visits never
create rows or overwrite the original attribution.
"""
import uuid
from urllib.parse import urlparse

from core.models import PageView
from core.security_middleware import _get_client_ip
from django.conf import settings
from django.core.cache import cache

# Cookie + cache key MUST match presentation/web/views.py (visitor_count tile).
_VISITOR_COOKIE = 'jk_visitor'
_COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year
_COUNT_CACHE_KEY = 'visitor_count'

# Paths that never represent a human page view.
_SKIP_PREFIXES = ('/static/', '/media/', '/api/', '/health', '/sitemap',
                  '/robots', '/favicon', '/.well-known')

# utm_source value (lowercased) → canonical label. Folds common aliases so
# `?utm_source=fb` and `?utm_source=facebook.com` both land on "facebook".
_UTM_ALIASES = {
    'fb': 'facebook', 'facebook': 'facebook', 'meta': 'facebook',
    'ig': 'instagram', 'instagram': 'instagram',
    'tg': 'telegram', 'telegram': 'telegram',
    'yt': 'youtube', 'youtube': 'youtube',
    'google': 'google', 'adwords': 'google', 'gads': 'google', 'gmb': 'google',
    'chatgpt': 'chatgpt', 'openai': 'chatgpt', 'gpt': 'chatgpt',
    'linkedin': 'linkedin', 'li': 'linkedin',
    'twitter': 'twitter', 'x': 'twitter',
    'github': 'github',
}

# Substring of the referrer host → canonical label. Checked after the short
# ambiguous hosts (x.com / t.co / t.me) which are matched exactly below.
_SOURCE_SUBSTR = (
    ('chatgpt', 'chatgpt'), ('openai', 'chatgpt'),
    ('google', 'google'),
    ('bing', 'bing'), ('yandex', 'yandex'), ('duckduckgo', 'duckduckgo'),
    ('facebook', 'facebook'), ('fb.com', 'facebook'),
    ('instagram', 'instagram'),
    ('youtube', 'youtube'), ('youtu.be', 'youtube'),
    ('linkedin', 'linkedin'), ('lnkd.in', 'linkedin'),
    ('github', 'github'),
    ('reddit', 'reddit'),
)

# Canonical source → brand colour. Shared by the admin badge (PageViewAdmin)
# and the dashboard sources breakdown so they never drift.
SOURCE_COLORS = {
    'google': '#4285F4', 'chatgpt': '#10a37f', 'facebook': '#1877F2',
    'instagram': '#E1306C', 'telegram': '#229ED9', 'youtube': '#FF0000',
    'twitter': '#1DA1F2', 'linkedin': '#0A66C2', 'github': '#6e5494',
    'bing': '#008373', 'yandex': '#FF3333', 'duckduckgo': '#DE5833',
    'reddit': '#FF4500', 'referral': '#b58900', 'direct': '#8a8a8a',
}


def source_color(source: str) -> str:
    return SOURCE_COLORS.get(source or 'direct', '#8a8a8a')


def _bare_host(host: str) -> str:
    host = (host or '').lower()
    return host[4:] if host.startswith('www.') else host


def classify_source(referrer: str, utm_source: str, host: str = '') -> str:
    """First-touch traffic source.

    Priority: explicit `utm_source` → referrer host → "direct". A referrer we
    recognise but don't map returns "referral"; same-site referrers are treated
    as direct (internal navigation).
    """
    u = (utm_source or '').strip().lower()
    if u:
        return _UTM_ALIASES.get(u, u[:32])

    if not referrer:
        return 'direct'
    try:
        ref_host = (urlparse(referrer).netloc or '').lower()
    except ValueError:
        return 'direct'
    if not ref_host:
        return 'direct'

    bare = _bare_host(ref_host)
    if host and bare == _bare_host(host):
        return 'direct'  # internal navigation
    if bare in ('x.com', 't.co') or 'twitter' in bare:
        return 'twitter'
    if bare == 't.me' or bare.endswith('.t.me') or 'telegram' in bare:
        return 'telegram'
    for needle, label in _SOURCE_SUBSTR:
        if needle in bare:
            return label
    return 'referral'


class VisitorTrackingMiddleware:
    """Record first-touch visitor attribution on every public HTML page.

    Replaces the home-only tracking that previously lived in HomeView.get():
    shared / deep links (e.g. /projects/<slug>) are now attributed too.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = f"/{getattr(settings, 'ADMIN_URL', 'admin/').strip('/')}/"

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._track(request, response)
        except Exception:
            pass  # attribution must never break a page render
        return response

    def _trackable(self, request, response) -> bool:
        if request.method != 'GET' or response.status_code != 200:
            return False
        path = request.path
        if path.startswith(self.admin_prefix) or path.startswith(_SKIP_PREFIXES):
            return False
        return 'text/html' in response.get('Content-Type', '')

    def _track(self, request, response):
        if not self._trackable(request, response):
            return

        cookie = request.COOKIES.get(_VISITOR_COOKIE)
        ip = _get_client_ip(request)
        real_ip = ip if ip and ip != '0.0.0.0' else None

        uid = None
        if cookie:
            try:
                uid = uuid.UUID(cookie)
            except ValueError:
                uid = None
            if uid and PageView.objects.filter(visitor_id=uid).exists():
                return  # returning visitor — keep original first-touch row
        elif real_ip:
            # No cookie but IP seen before (different browser / incognito):
            # bind this browser to the existing visitor, don't double-count.
            existing = PageView.objects.filter(ip_address=real_ip).first()
            if existing:
                self._set_cookie(response, existing.visitor_id)
                return

        # New visitor → capture attribution once.
        g = request.GET
        referrer = request.META.get('HTTP_REFERER', '')[:500]
        utm_source = g.get('utm_source', '')[:100]
        new_id = uid or uuid.uuid4()
        PageView.objects.create(
            visitor_id=new_id,
            ip_address=real_ip,
            source=classify_source(referrer, utm_source, host=request.get_host()),
            landing_path=request.path[:200],
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=g.get('utm_medium', '')[:100],
            utm_campaign=g.get('utm_campaign', '')[:100],
            utm_content=g.get('utm_content', '')[:100],
            utm_term=g.get('utm_term', '')[:100],
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        )
        cache.delete(_COUNT_CACHE_KEY)
        self._set_cookie(response, new_id)

    @staticmethod
    def _set_cookie(response, visitor_id):
        response.set_cookie(
            _VISITOR_COOKIE, str(visitor_id),
            max_age=_COOKIE_MAX_AGE, httponly=True, samesite='Lax',
        )
