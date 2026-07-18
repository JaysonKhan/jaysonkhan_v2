"""
Security middleware for Jaysonkhan application.
Provides additional security layers on top of Django's built-in security.
"""
import logging
import re

from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger('django.security')


def _get_client_ip(request):
    """
    Return the real client IP.

    Nginx is the single trusted reverse proxy and *overwrites* X-Real-IP with
    the real client IP ($remote_addr), so a client cannot spoof it. The raw
    X-Forwarded-For header, by contrast, is client-controlled (Nginx *appends*
    to it via $proxy_add_x_forwarded_for), so it must NOT be trusted for
    security checks — using it allows admin IP-restriction and rate-limit
    bypass via a spoofed leftmost entry.

    REMOTE_ADDR is empty here because Gunicorn binds a unix socket (no TCP
    peer), so X-Real-IP is the authoritative source.
    """
    return (
        request.META.get('HTTP_X_REAL_IP')
        or request.META.get('REMOTE_ADDR')
        or '0.0.0.0'
    )


class SecurityHeadersMiddleware:
    """
    Adds additional security headers that Django's SecurityMiddleware doesn't cover.
    Place AFTER django.middleware.security.SecurityMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Permissions-Policy — disable dangerous browser APIs
        response['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), payment=(), '
            'usb=(), magnetometer=(), gyroscope=(), accelerometer=()'
        )

        # Cross-Origin headers
        response['Cross-Origin-Resource-Policy'] = 'same-origin'

        # Cache-Control for sensitive pages
        if request.path.startswith(('/api/', '/auth/')):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'

        return response


class RequestSanitizationMiddleware:
    """
    Sanitize and validate incoming requests to prevent common attack vectors.
    Place early in MIDDLEWARE stack.
    """

    # Path traversal patterns
    PATH_TRAVERSAL = re.compile(r'\.\./|\.\.\\|%2e%2e|%252e%252e', re.IGNORECASE)

    # Null byte injection
    NULL_BYTE = re.compile(r'%00|\x00')

    # Maximum URL length
    MAX_URL_LENGTH = 2048

    # Blocked file extensions in URLs
    BLOCKED_EXTENSIONS = {'.php', '.asp', '.aspx', '.jsp', '.cgi', '.exe', '.bat', '.cmd', '.sh', '.py'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Block extremely long URLs (potential buffer overflow)
        if len(request.get_full_path()) > self.MAX_URL_LENGTH:
            logger.warning(
                '[Security] Blocked oversized URL from %s: %d chars',
                _get_client_ip(request), len(request.get_full_path())
            )
            return HttpResponseForbidden('Request URI too long')

        # Block null byte injection
        if self.NULL_BYTE.search(path) or self.NULL_BYTE.search(request.META.get('QUERY_STRING', '')):
            logger.warning('[Security] Null byte injection attempt from %s', _get_client_ip(request))
            return HttpResponseForbidden('Bad request')

        # Block path traversal
        if self.PATH_TRAVERSAL.search(path):
            logger.warning('[Security] Path traversal attempt from %s: %s', _get_client_ip(request), path)
            return HttpResponseForbidden('Bad request')

        # Block requests for non-Django file types
        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
        if f'.{ext}' in self.BLOCKED_EXTENSIONS:
            logger.warning('[Security] Blocked extension request from %s: %s', _get_client_ip(request), path)
            return HttpResponseForbidden('Not found')

        # Block common exploit paths
        blocked_paths = {
            '/wp-admin', '/wp-login', '/xmlrpc.php', '/phpmyadmin',
            '/adminer', '/.git', '/.svn', '/.env', '/.htaccess',
            '/cgi-bin', '/.well-known/security.txt',
        }
        lower_path = path.lower()
        for bp in blocked_paths:
            if lower_path.startswith(bp):
                return HttpResponseForbidden('Not found')

        return self.get_response(request)


class AdminIPRestrictionMiddleware:
    """
    Restrict admin panel access to whitelisted IPs.

    Effective allowlist = ADMIN_ALLOWED_IPS (.env base, needs restart to
    change) ∪ the bot-managed shared file (core.allowed_ips — applies
    immediately, no restart). The union is computed per request so an IP
    added via @Jaysonkhanbot works on the very next admin request.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_url = getattr(settings, 'ADMIN_URL_PREFIX', 'admin/')
        self.env_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])

    def __call__(self, request):
        if request.path.startswith(f'/{self.admin_url}'):
            from core.allowed_ips import get_dynamic_ips
            allowed = set(self.env_ips) | set(get_dynamic_ips())
            if allowed:
                client_ip = _get_client_ip(request)
                if client_ip not in allowed:
                    logger.warning(
                        '[Security] Admin access attempt from unauthorized IP: %s, path: %s',
                        client_ip, request.path
                    )
                    from django.http import Http404
                    raise Http404

        return self.get_response(request)
