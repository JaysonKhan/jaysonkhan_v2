# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal portfolio platform for a Flutter Mobile Engineer — Django 4.2 backend with SSR templates (Tailwind CSS) and a DRF JSON API. Production site: https://jaysonkhan.com

## Commands

```bash
# Dev server (from project root)
backend/venv/bin/python backend/manage.py runserver 0.0.0.0:8000

# Tailwind CSS
npm run css:build          # one-time build
npm run css:watch          # watch mode

# Django management
backend/venv/bin/python backend/manage.py makemigrations <app>
backend/venv/bin/python backend/manage.py migrate
backend/venv/bin/python backend/manage.py collectstatic --noinput

# Tests
backend/venv/bin/python backend/manage.py test                              # all
backend/venv/bin/python backend/manage.py test portfolio                    # single app
backend/venv/bin/python backend/manage.py test portfolio.tests.SkillModelTest  # single class
# Settings override: append --settings=config.settings.dev

# Production deploy (pushes, SSHes to server, migrates, restarts)
bash deploy.sh "commit message"
```

## Architecture

Clean Architecture with three layers:

```
backend/
├── config/settings/       # base.py → dev.py / prod.py (never read DEBUG from env)
├── apps/                  # Domain layer (models, services, repositories)
│   ├── core/              # SiteSettings singleton, security middleware, RichTextWidget, bleach sanitizer
│   ├── users/             # Custom User (email-based auth, not username)
│   ├── portfolio/         # Project, Skill, Experience + PortfolioRepository/Service
│   ├── blog/              # Post, Category, Tag
│   ├── contact/           # ContactMessage + honeypot spam protection + rate limiting
│   └── interactions/      # TelegramProfile, Comment (generic FK), Like, Reaction
└── presentation/          # Delivery layer
    ├── api/               # DRF ViewSets + Serializers (DefaultRouter)
    │   └── serializers.py # Full + lightweight "List" versions for infinite scroll
    └── web/               # SSR class-based views + Django templates
        └── templates/web/ # base.html, home, projects, blog, contact, partials
```

## Key Patterns

- **Repository + Service**: `PortfolioRepository` (queries) → `PortfolioService` (orchestration). Same pattern in `contact/services.py`.
- **SiteSettings Singleton**: Single-row model (pk=1), 80+ fields, 8-tab Unfold admin. Cached 5 min, invalidated on `post_save`. Accessed globally via `core.context_processors.site_settings`.
- **Visibility Flags**: `Project.is_visible`, `Project.is_featured`, `Project.is_bot`, `Post.is_published`, `SiteSettings.apps_section_visible` (toggles entire section via `AppsGuardMixin`).
- **Project Filtering**: Done by URL fields (app_store_url, play_store_url, web_page_url, is_bot) — no platform field.
- **Rich Text**: TinyMCE 6 (CDN) → upload to `/api/admin/media-upload/` → bleach sanitization on model save. CSRF token read from hidden input (not cookie, because `CSRF_COOKIE_HTTPONLY=True`).
- **Infinite Scroll**: `ProjectListSerializer` / `PostListSerializer` (lightweight) consumed by `static/js/infinite-scroll.js`.
- **Telegram Auth**: Login Widget → HMAC verification via `TELEGRAM_BOT_TOKEN` → session-based `TelegramProfile`.
- **Comments/Likes**: Generic FK (ContentType) — works on both Post and Project.

## Security

- **Middleware stack order matters**: `RequestSanitizationMiddleware` (first) → CORS → Django Security → `SecurityHeadersMiddleware` → Session → CSRF → Auth → `AdminIPRestrictionMiddleware`.
- **CSP**: Set in Nginx config (`/etc/nginx/sites-enabled/jaysonkhan`), not Django. `frame-src` must include any new embed domains (YouTube, etc.).
- **Admin access**: IP-restricted via `ADMIN_ALLOWED_IPS` env var. Admin URL is configurable via `ADMIN_URL` env.
- **API permissions**: Default `IsAdminUser`. Public endpoints override with `AllowAny` (projects list, contact create).

## Bot Admin (botproxy app)

Django admin panel for managing TalabaOvozi Telegram bot. Bot runs on same server as a separate systemd service.

```
apps/botproxy/
├── client.py       # BotAPIClient — HMAC-authenticated httpx client to bot API
├── views.py        # Dashboard, polls, universities, users, analytics views
├── urls.py         # /jk-dinadmin/bot/<svc>/...
└── templates/botproxy/
    ├── base.html           # Bot admin layout (dark theme, nav tabs)
    ├── dashboard.html      # Chart.js analytics dashboard
    ├── university_list.html # University cards with logo disk-serving
    └── ...
```

- **Bot API**: `http://127.0.0.1:8433` (aiohttp, localhost only)
- **Auth**: HMAC-SHA256 (`BOT_API_SECRET_KEY`)
- **Logos**: Saved to `/var/www/jaysonkhan/media/uni_logos/talabaovozi/`, served by nginx `/media/`. View annotates `logo_url` for direct media path (avoids Django proxy → 503 issue with sync workers).
- **Dashboard charts**: Chart.js 4.x (CDN), AJAX lazy-load for poll analytics

## Botproxy Staff & Feedback (added 2026-04-05)

- Staff CRUD views: staff_list, staff_create, staff_detail, staff_edit, staff_delete, staff_photo_proxy
- Staff form: position/department selects (from API), faculty dropdown (JS-filtered by university), time picker, phone format
- Staff list filters: university, position_code, name search
- Feedback dashboard: per-poll sentiment summary
- Staff photo disk cache: /media/staff_photos/{svc}/{id}.jpg — avoids repeated API proxy calls
- University detail page includes staff list section
- SiteSettings uses abstract mixins (BrandingMixin, SEOMixin, etc.) — NOT separate models. No migration needed.

## Gotchas

- NEVER use async views with Gunicorn sync workers + @staff_member_required — causes "coroutine was never awaited" 500 error
- Use ThreadPoolExecutor for parallel bot API calls (not asyncio.gather) under WSGI/Gunicorn sync
- Staff photo proxy: always disk-cache to /media/staff_photos/ — 260 staff × parallel img loads kills Gunicorn workers
- Deploy --bot uses `deploy` user git (not sudo) — GitHub SSH key is on deploy user only
- Bot API at 127.0.0.1:8433 — never exposed externally. Django connects via httpx with HMAC-SHA256 auth

## Production

- **Server**: Ubuntu 24.04 at 144.91.69.225, SSH alias `jaysonkhan`
- **Stack**: Gunicorn (3 sync workers) → Nginx → PostgreSQL
- **Settings module**: `config.settings.prod` (set in wsgi.py and systemd unit)
- **Nginx config**: `security/nginx/jaysonkhan.conf` (keep in sync with server)
- **deploy.sh**: Unified deploy script
  - `./deploy.sh` — Django only (git push → pull → pip → css:build → migrate → collectstatic → restart)
  - `./deploy.sh --bot` — Bot only (push hokimiyatbot → pull on server → restart talabaovozi)
  - `./deploy.sh --all` — Both services
- **Static/Media**: Nginx serves from `/var/www/jaysonkhan/static` and `/var/www/jaysonkhan/media`
- **Architecture doc**: See `~/JaysonServer/SERVER_ARCHITECTURE.md` for full server layout

## Environment Variables

Core: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `ADMIN_URL`, `ADMIN_ALLOWED_IPS`
Database: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`
Email: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
Bot: `BOT_API_BASE_URL` (default: http://127.0.0.1:8433), `BOT_API_SECRET_KEY`, `BOT_API_TIMEOUT`
