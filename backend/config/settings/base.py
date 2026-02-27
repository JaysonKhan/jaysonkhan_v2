import os
import sys
import environ
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Add apps directory to sys.path
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Initialize environ
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, 'env-key-missing'),
    DATABASE_URL=(str, f'sqlite:///{BASE_DIR}/db.sqlite3'),
)

# Read .env file from project root
environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

SECRET_KEY = env('DJANGO_SECRET_KEY')

# DEBUG is always False in base — only dev.py explicitly enables it.
# Never read DEBUG from environment: if the wrong settings module is used on prod,
# debug pages must never be shown to end users.
DEBUG = False

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Application definition
INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # Local apps
    'users',
    'portfolio',
    'blog',
    'contact',
    'core',
    'interactions',
]

MIDDLEWARE = [
    'core.security_middleware.RequestSanitizationMiddleware',  # Must be first: blocks malicious requests early
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'core.security_middleware.SecurityHeadersMiddleware',  # Additional security headers
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.security_middleware.AdminIPRestrictionMiddleware',  # Admin IP whitelist
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'presentation' / 'web' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_settings',
                'interactions.context_processors.tg_profile',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
default_db = env.db()

# Normalize relative sqlite paths to BASE_DIR so commands run from any cwd
# always point to the same database file.
if default_db.get('ENGINE') == 'django.db.backends.sqlite3':
    db_name = default_db.get('NAME')
    if db_name and not os.path.isabs(db_name):
        default_db['NAME'] = str(BASE_DIR / db_name)

DATABASES = {
    'default': default_db,
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# Source static files (project-level) — picked up by collectstatic
STATICFILES_DIRS = [BASE_DIR / 'static']
# Destination for collectstatic — must differ from STATICFILES_DIRS paths
STATIC_ROOT = env('STATIC_ROOT', default=str(BASE_DIR / 'staticfiles'))

MEDIA_URL = '/media/'
MEDIA_ROOT = env('MEDIA_ROOT', default=str(BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache — LocMemCache (single-process, per-worker).
# Swap BACKEND to redis://... in production for shared multi-worker caching.
CACHES = {
    'default': {
        'BACKEND': env(
            'CACHE_BACKEND',
            default='django.core.cache.backends.locmem.LocMemCache',
        ),
        'LOCATION': env('CACHE_LOCATION', default='jaysonkhan-default'),
    }
}

# CORS Settings
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])
CORS_ALLOW_ALL_ORIGINS = False  # NEVER set to True
CORS_ALLOW_CREDENTIALS = True

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# ── Session & Cookie Security ────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Admin IP Restriction (empty list = no restriction in dev) ────────────────
ADMIN_ALLOWED_IPS = env.list('ADMIN_ALLOWED_IPS', default=[])
ADMIN_URL_PREFIX = env('ADMIN_URL', default='admin/')

# ── File Upload Security ─────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Telegram Bot Token — used to verify Login Widget signatures
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_BOT_USERNAME = env('TELEGRAM_BOT_USERNAME', default='')

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # All API endpoints require admin authentication by default.
    # Individual views that need public access must explicitly override
    # permission_classes = [permissions.AllowAny] (e.g. ContactMessageViewSet.create)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAdminUser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        # JSON only — disables the browsable API HTML interface entirely.
        # This prevents leaking schema/route info to unauthenticated visitors.
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    # Rate limiting — basic protection against enumeration / DoS
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',
        'user': '300/min',
    },
}

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME', default=5)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME', default=30)),
}

# Email configuration
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@jaysonkhan.com')

# Django Unfold Admin Theme
UNFOLD = {
    "SITE_TITLE": env("UNFOLD_SITE_TITLE", default="Portfolio Admin"),
    "SITE_HEADER": env("UNFOLD_SITE_HEADER", default="Portfolio Admin"),
    "SITE_URL": "/",
    "SITE_SYMBOL": "smartphone",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "LOGIN": {
        "image": lambda r: "/static/images/hero.jpg",
        "redirect_after": lambda r: "/admin/",
    },
    "COLORS": {
        "primary": {
            "50":  "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Site",
                "separator": True,
                "items": [
                    {
                        "title": "Site Settings",
                        "icon": "settings",
                        "link": "/admin/core/sitesettings/",
                    },
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "items": [
                    {
                        "title": "Projects",
                        "icon": "folder_open",
                        "link": "/admin/portfolio/project/",
                    },
                    {
                        "title": "Skills",
                        "icon": "star",
                        "link": "/admin/portfolio/skill/",
                    },
                    {
                        "title": "Experience",
                        "icon": "work",
                        "link": "/admin/portfolio/experience/",
                    },
                    {
                        "title": "Blog Posts",
                        "icon": "article",
                        "link": "/admin/blog/post/",
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/blog/category/",
                    },
                    {
                        "title": "Tags",
                        "icon": "label",
                        "link": "/admin/blog/tag/",
                    },
                    {
                        "title": "Contact Messages",
                        "icon": "mail",
                        "link": "/admin/contact/contactmessage/",
                    },
                ],
            },
            {
                "title": "Interactions",
                "separator": True,
                "items": [
                    {
                        "title": "Comments",
                        "icon": "forum",
                        "link": "/admin/interactions/comment/",
                    },
                    {
                        "title": "Likes",
                        "icon": "favorite",
                        "link": "/admin/interactions/like/",
                    },
                    {
                        "title": "Telegram Profiles",
                        "icon": "group",
                        "link": "/admin/interactions/telegramprofile/",
                    },
                ],
            },
            {
                "title": "Authentication",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/users/user/",
                    },
                ],
            },
        ],
    },
}
