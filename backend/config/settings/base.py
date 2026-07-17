import os
import sys
from pathlib import Path

import environ
from django.templatetags.static import static

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
    'modeltranslation',  # Must come BEFORE django.contrib.admin (registers tabbed admin)
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # Third party
    'rosetta',
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
    'telegram',
    'servermonitor',
    'ops',
]

MIDDLEWARE = [
    'core.security_middleware.RequestSanitizationMiddleware',  # Must be first: blocks malicious requests early
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'core.security_middleware.SecurityHeadersMiddleware',  # Additional security headers
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # i18n: must come AFTER session, BEFORE common
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.security_middleware.AdminIPRestrictionMiddleware',  # Admin IP whitelist
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.tracking.VisitorTrackingMiddleware',  # First-touch visitor attribution (last: only acts on final 200 HTML GET)
    # XFrameOptionsMiddleware removed: CSP frame-ancestors in Nginx handles
    # clickjacking protection and allows Telegram Mini App iframes.
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
# Default = Khorezm dialect ('xo' — custom code, not ISO 639).
# Languages: Khorezm dialect (xo), standard Uzbek (uz), Russian (ru), English (en).
LANGUAGE_CODE = 'xo'
LANGUAGES = [
    ('xo', "Xorazmcha"),       # Khorezm dialect — DEFAULT
    ('uz', "O'zbekcha"),       # Standard Uzbek (Latin)
    ('ru', "Русский"),         # Russian
    ('en', "English"),         # English
]
# 'xo' is not in Django's built-in LANG_INFO. The actual patch runs in
# core.apps.CoreConfig.ready() — see that method for why settings-time
# patching was unreliable.
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# django-rosetta — admin UI for .po file management
ROSETTA_SHOW_AT_ADMIN_PANEL = True
ROSETTA_STORAGE_CLASS = 'rosetta.storage.CacheRosettaStorage'
ROSETTA_AUTO_COMPILE = True          # .mo auto-compile on save (no restart needed)
ROSETTA_ENABLE_TRANSLATION_SUGGESTIONS = False  # no Google Translate API needed
ROSETTA_REQUIRES_AUTH = True

# django-modeltranslation — translate model fields per language
MODELTRANSLATION_DEFAULT_LANGUAGE = 'xo'
MODELTRANSLATION_LANGUAGES = ('xo', 'uz', 'ru', 'en')
# Active-language column is ALWAYS tried first; fall back only if empty.
# (Tuple form would force `xo` to win for ALL active languages — bug.)
MODELTRANSLATION_FALLBACK_LANGUAGES = {
    'default': ('xo',),  # for any active lang: if empty, fall back to xo
}
MODELTRANSLATION_TRANSLATION_FILES = (
    'core.translations',
    'portfolio.translations',
    'blog.translations',
)

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
ADMIN_ALLOWED_IPS = [ip.strip() for ip in env.list('ADMIN_ALLOWED_IPS', default=[]) if ip.strip()]
ADMIN_URL_PREFIX = env('ADMIN_URL', default='admin/')

# ── File Upload Security ─────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # TranslationAdmin × 4 langs × many fields; 200 was too low
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Telegram Bot Token — used to verify Login Widget signatures
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_BOT_USERNAME = env('TELEGRAM_BOT_USERNAME', default='')
# Mini App short name (BotFather /newapp da o'rnatiladi)
TELEGRAM_WEBAPP_SHORT_NAME = env('TELEGRAM_WEBAPP_SHORT_NAME', default='app')
# Max age (seconds) for Telegram auth_date — reject older tokens (default 24h)
TELEGRAM_AUTH_MAX_AGE_SECONDS = env.int('TELEGRAM_AUTH_MAX_AGE_SECONDS', default=86400)
# Webhook secret & domain for bot notifications
TELEGRAM_WEBHOOK_SECRET = env('TELEGRAM_WEBHOOK_SECRET', default='')
TELEGRAM_WEBHOOK_DOMAIN = env('TELEGRAM_WEBHOOK_DOMAIN', default='https://jaysonkhan.com')

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

# ── Logging ──────────────────────────────────────────────────────────────────
# Console logger for dev; file logger added in prod.py for production.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        # App-level loggers — capture INFO+ for our own code
        'core': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'portfolio': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'blog': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'contact': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'interactions': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

# Django Unfold Admin Theme
# Admin URL prefix — read from .env so sidebar links always match the real URL.
_ADMIN_URL = env('ADMIN_URL', default='admin/')
_A = '/' + _ADMIN_URL  # e.g. '/jk-dinadmin/'

UNFOLD = {
    "SITE_TITLE": env("UNFOLD_SITE_TITLE", default="JK-DinAdmin"),
    "SITE_HEADER": env("UNFOLD_SITE_HEADER", default="JK-DinAdmin"),
    "SITE_SUBHEADER": "v4 · XIVA INK · OWNER",
    "SITE_URL": "/",
    "SITE_SYMBOL": "auto_awesome",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "BORDER_RADIUS": "6px",
    # XIVA INK is a single universal dark-ink scheme — hide Unfold's toggle.
    "THEME": "dark",
    # XIVA INK overlay loaded on top of Unfold's tailwind base
    "STYLES": [
        lambda request: static("admin/css/editorial.css"),
    ],
    "SCRIPTS": [
        lambda request: static("admin/js/theme-bootstrap.js"),
    ],
    "DASHBOARD_CALLBACK": "core.dashboard.dashboard_callback",
    "LOGIN": {
        "image": lambda r: static("images/hero.jpg"),
        "redirect_after": lambda r: "/" + env('ADMIN_URL', default='admin/'),
    },
    # XIVA INK palette — Khiva terracotta oklch(0.71 0.135 45) as primary.
    # oklch format required by Unfold 0.67 + Tailwind v4 for opacity utilities.
    "COLORS": {
        "primary": {
            "50":  "oklch(97% .015 45)",
            "100": "oklch(93% .035 45)",
            "200": "oklch(86% .065 45)",
            "300": "oklch(79% .105 45)",
            "400": "oklch(75% .12 45)",
            "500": "oklch(71% .135 45)",   # Khiva terracotta (design --accent)
            "600": "oklch(64% .15 42)",    # --accent-strong
            "700": "oklch(52% .13 42)",
            "800": "oklch(42% .105 42)",
            "900": "oklch(32% .08 42)",
            "950": "oklch(22% .055 42)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        # ── Navigation organized by daily-usage frequency ────────────────────
        # 1. Boshqaruv  — entry point (Dashboard, Tashriflar)
        # 2. Kontent    — daily content edits (Blog, Projects, Team, Media)
        # 3. Aloqa      — inbox (Xabarlar, Komentariyalar, Layklar) [BADGES]
        # 4. Sozlamalar — less-frequent setup (Site, Skills, Categories, Tags)
        # 5. Bot        — TalabaOvozi service (Bot, Telegram session, Emoji)
        # 6. Tizim      — rare admin (Cron, Users, Bans, Telegram entities, OSINT)
        "navigation": [
            {
                "title": "Boshqaruv",
                "separator": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": _A,
                        "permission": lambda r: r.user.is_active and r.user.is_staff,
                    },
                    {
                        "title": "Tashriflar",
                        "icon": "trending_up",
                        "link": f"{_A}core/pageview/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "UTM linklar",
                        "icon": "add_link",
                        "link": f"{_A}core/pageview/utm-builder/",
                        "permission": lambda r: r.user.is_staff,
                    },
                ],
            },
            {
                "title": "Kontent",
                "separator": True,
                "items": [
                    {
                        "title": "Blog yozuvlari",
                        "icon": "edit_note",
                        "link": f"{_A}blog/post/",
                        "permission": lambda r: r.user.has_perm("blog.view_post"),
                    },
                    {
                        "title": "Loyihalar",
                        "icon": "folder_open",
                        "link": f"{_A}portfolio/project/",
                        "permission": lambda r: r.user.has_perm("portfolio.view_project"),
                    },
                    {
                        "title": "Jamoa",
                        "icon": "groups",
                        "link": f"{_A}portfolio/teammember/",
                        "permission": lambda r: r.user.has_perm("portfolio.view_teammember"),
                    },
                    {
                        "title": "Galereya devori",
                        "icon": "photo_library",
                        "link": f"{_A}portfolio/galleryimage/",
                        "permission": lambda r: r.user.has_perm("portfolio.view_galleryimage"),
                    },
                    {
                        "title": "Media kutubxonasi",
                        "icon": "image",
                        "link": f"{_A}core/asset/manager/",
                        "permission": lambda r: r.user.has_perm("core.view_asset"),
                    },
                ],
            },
            {
                "title": "Aloqa",
                "separator": True,
                "items": [
                    {
                        "title": "Xabarlar",
                        "icon": "inbox",
                        "link": f"{_A}contact/contactmessage/",
                        "badge": "core.dashboard.unread_messages_badge",
                        "permission": lambda r: r.user.has_perm("contact.view_contactmessage"),
                    },
                    {
                        "title": "Komentariyalar",
                        "icon": "forum",
                        "link": f"{_A}interactions/comment/",
                        "badge": "core.dashboard.pending_comments_badge",
                        "permission": lambda r: r.user.has_perm("interactions.view_comment"),
                    },
                    {
                        "title": "Layklar",
                        "icon": "favorite",
                        "link": f"{_A}interactions/like/",
                        "permission": lambda r: r.user.has_perm("interactions.view_like"),
                    },
                    {
                        "title": "Reaksiyalar",
                        "icon": "add_reaction",
                        "link": f"{_A}interactions/commentreaction/",
                        "permission": lambda r: r.user.has_perm(
                            "interactions.view_commentreaction"
                        ),
                    },
                    {
                        "title": "Kanal ulashishlar",
                        "icon": "share",
                        "link": f"{_A}interactions/channelshare/",
                        "permission": lambda r: r.user.has_perm(
                            "interactions.view_channelshare"
                        ),
                    },
                ],
            },
            {
                "title": "Sayt konfiguratsiyasi",
                "separator": True,
                "items": [
                    {
                        "title": "Brending",
                        "icon": "palette",
                        "link": f"{_A}core/sitesettingsbranding/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "SEO & Analitika",
                        "icon": "search",
                        "link": f"{_A}core/sitesettingsseo/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Navigatsiya & Footer",
                        "icon": "menu",
                        "link": f"{_A}core/sitesettingsnavigation/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Bosh sahifa",
                        "icon": "home",
                        "link": f"{_A}core/sitesettingshomepage/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Aloqa & Ijtimoiy",
                        "icon": "contact_page",
                        "link": f"{_A}core/sitesettingscontact/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Telegram Bot",
                        "icon": "smart_toy",
                        "link": f"{_A}core/sitesettingstelegram/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Emoji sozlamalari",
                        "icon": "emoji_emotions",
                        "link": f"{_A}core/sitesettingsemoji/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Editorial v3",
                        "icon": "article",
                        "link": f"{_A}core/sitesettingseditorial/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                ],
            },
            {
                "title": "Sozlamalar",
                "separator": True,
                "items": [
                    {
                        "title": "Skill",
                        "icon": "star",
                        "link": f"{_A}portfolio/skill/",
                        "permission": lambda r: r.user.has_perm("portfolio.view_skill"),
                    },
                    {
                        "title": "Tajriba",
                        "icon": "work",
                        "link": f"{_A}portfolio/experience/",
                        "permission": lambda r: r.user.has_perm("portfolio.view_experience"),
                    },
                    {
                        "title": "Blog kategoriyalari",
                        "icon": "category",
                        "link": f"{_A}blog/category/",
                        "permission": lambda r: r.user.has_perm("blog.view_category"),
                    },
                    {
                        "title": "Blog teglari",
                        "icon": "label",
                        "link": f"{_A}blog/tag/",
                        "permission": lambda r: r.user.has_perm("blog.view_tag"),
                    },
                    {
                        "title": "Notifikatsiya sozlamalari",
                        "icon": "notifications",
                        "link": f"{_A}interactions/notificationpreference/",
                        "permission": lambda r: r.user.has_perm("interactions.view_notificationpreference"),
                    },
                ],
            },
            {
                "title": "Tizim",
                "separator": True,
                "items": [
                    {
                        "title": "Cron jadvallar",
                        "icon": "schedule",
                        "link": f"{_A}ops/managedcron/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Cron tarixi",
                        "icon": "history",
                        "link": f"{_A}ops/cronrun/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Foydalanuvchilar",
                        "icon": "person",
                        "link": f"{_A}users/user/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Bans",
                        "icon": "block",
                        "link": f"{_A}interactions/userban/",
                        "permission": lambda r: r.user.has_perm("interactions.view_userban"),
                    },
                    {
                        "title": "Telegram entities",
                        "icon": "group",
                        "link": f"{_A}telegram/telegramentity/",
                        "permission": lambda r: r.user.has_perm("telegram.view_telegramentity"),
                    },
                    {
                        "title": "Server xizmatlari",
                        "icon": "monitor_heart",
                        "link": f"{_A}servermonitor/servicecheckresult/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                    {
                        "title": "Telegram log xabarlari",
                        "icon": "receipt_long",
                        "link": f"{_A}interactions/adminlogmessage/",
                        "permission": lambda r: r.user.has_perm(
                            "interactions.view_adminlogmessage"
                        ),
                    },
                    {
                        "title": "Guruhlar (huquqlar)",
                        "icon": "admin_panel_settings",
                        "link": f"{_A}auth/group/",
                        "permission": lambda r: r.user.is_superuser,
                    },
                ],
            },
        ],
    },
}
