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

# Lokal/test: bo'sh admin IP-ro'yxati panelni yopmaydi (prod'da yopadi — security_middleware).
ADMIN_GATE_FAIL_CLOSED = False

# Voice agent demo: runserver can't serve the WebSocket — run the relay next to it:
#   cd backend && venv/bin/uvicorn presentation.realtime.voice_agent:app --port 8765
VOICE_AGENT_WS_URL = env('VOICE_AGENT_WS_URL', default='ws://127.0.0.1:8765/demos/voice-agent/ws')
