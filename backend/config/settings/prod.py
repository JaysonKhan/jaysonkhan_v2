from .base import *
import os

DEBUG = False

# ── Security headers ──────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Prevent clickjacking but allow Telegram widget callback (SAMEORIGIN allows our own iframes)
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Allow OAuth popups (Telegram) to communicate back to the parent window
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# ── Allowed hosts ─────────────────────────────────────────────────────────────
ALLOWED_HOSTS = ['jaysonkhan.com', 'www.jaysonkhan.com', '144.91.69.225']

# ── Logging: hide internal details from responses ─────────────────────────────
# In prod Django already hides tracebacks (DEBUG=False).
# Add server-side logging to a file so errors are still visible to you:
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)  # create the directory if it doesn't exist yet

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
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
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
}

