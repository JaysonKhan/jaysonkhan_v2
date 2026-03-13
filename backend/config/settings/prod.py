from .base import *
import os

DEBUG = False

# ── Security headers (OWASP + CIS Benchmark) ─────────────────────────────────
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# HSTS: 1 year, include subdomains, preload-ready
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Prevent clickjacking — allow Telegram widget iframe via SAMEORIGIN
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Allow OAuth popups (Telegram) to communicate back to the parent window
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# ── CSRF Trusted Origins ─────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    'https://jaysonkhan.com',
    'https://www.jaysonkhan.com',
]

# ── Session Security ─────────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ── CSRF Cookie ──────────────────────────────────────────────────────────────
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Content Security Policy (Django header via SecurityMiddleware) ────────────
# Note: Primary CSP is set in Nginx. This is a fallback.
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ── Allowed hosts (strict whitelist) ─────────────────────────────────────────
ALLOWED_HOSTS = ['jaysonkhan.com', 'www.jaysonkhan.com', '144.91.69.225']

# ── CORS (strict whitelist, no wildcards) ────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'https://jaysonkhan.com',
    'https://www.jaysonkhan.com',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # NEVER set to True in production

# ── Proxy headers (Nginx is trusted reverse proxy) ───────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# ── Password validation (enhanced) ──────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ── File Upload Security ─────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100              # Prevent HashDoS via many fields
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# ── Rate Limiting (DRF) — production thresholds ─────────────────────────────
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/min',      # Stricter for anonymous users
        'user': '200/min',
    },
}

# ── Logging: server-side only, never expose to users ─────────────────────────
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_errors.log'),
            'formatter': 'verbose',
            'delay': True,
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'security.log'),
            'formatter': 'security',
            'delay': True,
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        # App-level loggers — catch WARNING+ in production log files
        'core': {'handlers': ['file'], 'level': 'WARNING', 'propagate': False},
        'portfolio': {'handlers': ['file'], 'level': 'WARNING', 'propagate': False},
        'blog': {'handlers': ['file'], 'level': 'WARNING', 'propagate': False},
        'contact': {'handlers': ['file'], 'level': 'WARNING', 'propagate': False},
        'interactions': {'handlers': ['file'], 'level': 'WARNING', 'propagate': False},
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
}

# ── Cache: use Redis in production ───────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'jaysonkhan-prod',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        },
    }
}

# ── Admin customization ─────────────────────────────────────────────────────
# Ensure admin URL is not 'admin/' — must be customized via ADMIN_URL env var
# The URL is read from .env in config/urls.py (default is 'admin/' ONLY for dev)
