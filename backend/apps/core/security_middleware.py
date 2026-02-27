"""
Security middleware for Jaysonkhan application.
Provides additional security layers on top of Django's built-in security.
"""
import logging
import re
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse

logger = logging.getLogger('django.security')


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

    # Common SQL injection patterns
    SQL_PATTERNS = re.compile(
        r"(?:')|(?:--)|(?:#)|(?:;)|"
        r"(?:(?:UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\s)",
        re.IGNORECASE
    )

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
                self._get_ip(request), len(request.get_full_path())
            )
            return HttpResponseForbidden('Request URI too long')

        # Block null byte injection
        if self.NULL_BYTE.search(path) or self.NULL_BYTE.search(request.META.get('QUERY_STRING', '')):
            logger.warning('[Security] Null byte injection attempt from %s', self._get_ip(request))
            return HttpResponseForbidden('Bad request')

        # Block path traversal
        if self.PATH_TRAVERSAL.search(path):
            logger.warning('[Security] Path traversal attempt from %s: %s', self._get_ip(request), path)
            return HttpResponseForbidden('Bad request')

        # Block requests for non-Django file types
        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
        if f'.{ext}' in self.BLOCKED_EXTENSIONS:
            logger.warning('[Security] Blocked extension request from %s: %s', self._get_ip(request), path)
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

    def _get_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class AdminIPRestrictionMiddleware:
    """
    Restrict admin panel access to whitelisted IPs.
    Configure ADMIN_ALLOWED_IPS in settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_url = getattr(settings, 'ADMIN_URL_PREFIX', 'admin/')
        self.allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])

    def __call__(self, request):
        if self.allowed_ips and request.path.startswith(f'/{self.admin_url}'):
            client_ip = self._get_ip(request)
            if client_ip not in self.allowed_ips:
                logger.warning(
                    '[Security] Admin access attempt from unauthorized IP: %s, path: %s',
                    client_ip, request.path
                )
                from django.http import Http404
                raise Http404

        return self.get_response(request)

    def _get_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
