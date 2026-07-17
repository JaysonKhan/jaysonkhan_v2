from .base import *

# ── Local development only ────────────────────────────────────────────────────
# wsgi.py defaults to prod. To use these settings locally, run:
#   DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py runserver
# Or set it in your shell: export DJANGO_SETTINGS_MODULE=config.settings.dev
DEBUG = False

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# DEBUG=False bo'lsa ham lokal runserver media'ni bersin (config/urls.py o'qiydi).
# Prod'da nginx /media/ ni beradi — bu bayroq faqat dev'da yoqiladi.
SERVE_MEDIA = True

# Additional dev settings here
