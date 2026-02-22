from .base import *

# ── Local development only ────────────────────────────────────────────────────
# wsgi.py defaults to prod. To use these settings locally, run:
#   DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py runserver
# Or set it in your shell: export DJANGO_SETTINGS_MODULE=config.settings.dev
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Additional dev settings here
