# jaysonkhan_v2 — CLAUDE.md

## 1. What this project is

Personal portfolio platform for a Flutter Mobile Engineer.
Production: **https://jaysonkhan.com** — 4 languages (xo/uz/ru/en), SSR-first
Django site with a small DRF API for infinite scroll, plus an admin panel
that proxies the [hokimiyatbot](../hokimiyatbot/) Telegram bot and a
psutil-based server monitor.

## 2. Tech stack

| Layer        | Technology                                               |
|--------------|----------------------------------------------------------|
| Backend      | Django 4.2 + Gunicorn (3 sync workers)                   |
| Database     | PostgreSQL                                               |
| Auth         | Email-based custom User + Telegram Login Widget (HMAC)   |
| Admin        | django-unfold (8-tab SiteSettings)                       |
| API          | DRF 3.16 + SimpleJWT                                     |
| Templates    | Django SSR + Tailwind CSS 4 (CLI build)                  |
| Rich text    | TinyMCE 6 (CDN) + bleach sanitizer                       |
| i18n         | django-modeltranslation (9 models, 4 langs, hreflang)    |
| Charts       | Chart.js 4 (CDN)                                         |
| Server tools | psutil (CPU/RAM/disk metrics)                            |
| Web server   | Nginx (TLS, static, media, CSP headers)                  |
| Python       | 3.12 (server)                                            |

## 3. Folder structure

```
jaysonkhan_v2/
├── backend/
│   ├── manage.py
│   ├── config/
│   │   └── settings/         base.py → dev.py / prod.py (split, not env-toggled)
│   ├── apps/                 Domain layer
│   │   ├── core/             SiteSettings singleton, security middleware,
│   │   │                     RichTextWidget, bleach sanitizer
│   │   ├── users/            custom User (email auth, no username)
│   │   ├── portfolio/        Project, Skill, Experience + Repository/Service
│   │   ├── blog/             Post, Category, Tag
│   │   ├── contact/          ContactMessage + honeypot + rate limit
│   │   ├── interactions/     TelegramProfile, Comment (generic FK), Like, Reaction
│   │   ├── botproxy/         Admin panel for hokimiyatbot (HMAC client + views)
│   │   ├── servermonitor/    psutil metrics + Telegram /status, /tariff, /logs
│   │   ├── telegram/         Telegram bot helpers / webhook glue
│   │   ├── osint/             OSINT lookups (private)
│   │   └── ops/              ad-hoc ops/cron utilities
│   ├── presentation/         Delivery layer
│   │   ├── api/              DRF ViewSets + Serializers (DefaultRouter)
│   │   │                     Full + lightweight "List" serializers for infinite scroll
│   │   └── web/              SSR class-based views
│   │       └── templates/web/  base.html, home, projects, blog, contact, partials
│   ├── locale/               .po/.mo (xo, uz, ru, en)
│   ├── static/ staticfiles/  Tailwind output (`output.css`), JS, images
│   └── media/                user uploads (rich-text inline media, project covers)
├── docs/                     human docs
├── security/
│   └── nginx/jaysonkhan.conf nginx config (kept in sync with server)
├── presentation/             additional templates / partials
├── server-manager.sh         server health / restart helpers
├── deploy.sh                 unified deploy (web / --bot / --all)
├── tailwind.config.js        + tailwind.input.css
├── package.json              Tailwind 4 CLI build only
└── requirements.txt
```

## 4. Patterns & conventions

- **Clean Architecture split** — `apps/` is the domain layer (models, services, repositories), `presentation/` is the delivery layer (views, serializers, templates). Don't put templates inside `apps/`.
- **Settings split, not env toggle** — `config/settings/base.py` → `dev.py` / `prod.py`. Never read `DEBUG` from env in `base.py`. Production sets `DJANGO_SETTINGS_MODULE=config.settings.prod`.
- **Repository + Service** — `PortfolioRepository` (queries) → `PortfolioService` (orchestration). Same pattern in `contact/services.py`.
- **SiteSettings singleton** — single-row model (`pk=1`), 80+ fields organised via abstract mixins (`BrandingMixin`, `SEOMixin`, etc. — NOT separate models). Cached 5 min, invalidated on `post_save`. Read globally via `core.context_processors.site_settings`.
- **Visibility flags** — `Project.is_visible`, `is_featured`, `is_bot`; `Post.is_published`; `SiteSettings.apps_section_visible` (toggles entire Apps section via `AppsGuardMixin`).
- **Project filtering** — by URL fields (`app_store_url`, `play_store_url`, `web_page_url`, `is_bot`). No `platform` field.
- **Rich text** — TinyMCE 6 CDN → `/api/admin/media-upload/` → bleach sanitization on `save()`. CSRF token read from a hidden input (NOT cookie, because `CSRF_COOKIE_HTTPONLY=True`).
- **Infinite scroll** — `ProjectListSerializer` / `PostListSerializer` (lightweight) consumed by `static/js/infinite-scroll.js`.
- **Telegram auth** — Login Widget → HMAC verify with `TELEGRAM_BOT_TOKEN` → session-based `TelegramProfile`.
- **Comments / likes / reactions** — generic FK (ContentType), works on both `Post` and `Project`.
- **i18n** — 9 models translated with `django-modeltranslation`, real per-language URLs, `hreflang` alternates, plus `Person.alternateName` (10 ism varianti) for SEO.
- **AI-bot policy** — opposite of EduStats: `robots.txt` BLOCKS AI bots here (not allow).

## 5. How to run

### Local dev

```bash
# 1. Backend
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
# (default settings module = config.settings.dev)

# 2. Tailwind (separate terminal)
npm install
npm run css:watch         # dev
npm run css:build         # one-shot prod build
```

### Common Django commands

```bash
# from project root
backend/venv/bin/python backend/manage.py makemigrations <app>
backend/venv/bin/python backend/manage.py migrate
backend/venv/bin/python backend/manage.py collectstatic --noinput
```

### Tests

```bash
backend/venv/bin/python backend/manage.py test
backend/venv/bin/python backend/manage.py test portfolio
backend/venv/bin/python backend/manage.py test portfolio.tests.SkillModelTest
# Override settings: append --settings=config.settings.dev
```

### Deploy

```bash
./deploy.sh "commit message"   # Django only (push → pull → pip → css:build → migrate → collectstatic → restart)
./deploy.sh --bot              # hokimiyatbot only
./deploy.sh --all              # both services
```

### Server monitor (Telegram bot commands — owner-only)

```
/status       /services    /disk    /tariff
/logs [service] [lines]    /backup
```

Backed by management commands:
```bash
python manage.py server_health_report [--quick] [--tariff] [--alert-only]
python manage.py check_cpu_alert [--threshold N]
python manage.py register_bot_commands
```

## 6. Important things to keep in mind

### Architecture invariants
1. **Middleware order matters** — `RequestSanitizationMiddleware` (first) → CORS → Django Security → `SecurityHeadersMiddleware` → Session → CSRF → Auth → `AdminIPRestrictionMiddleware`.
2. **CSP lives in Nginx**, not Django. New iframe embeds (YouTube etc.) require updating `frame-src` in `security/nginx/jaysonkhan.conf` AND on the server.
3. **Admin URL is configurable** via `ADMIN_URL` env; admin is also IP-restricted via `ADMIN_ALLOWED_IPS`.
4. **API permissions** — default `IsAdminUser`. Public endpoints (`projects`, `contact`) explicitly override with `AllowAny`.

### Common bugs to avoid
5. **NEVER use async views with Gunicorn sync workers + `@staff_member_required`** — fires "coroutine was never awaited" 500.
6. **Parallel bot API calls** — use `ThreadPoolExecutor`, NOT `asyncio.gather`, under sync WSGI/Gunicorn.
7. **Staff photo proxy** — always disk-cache to `/media/staff_photos/` (`260 staff × parallel <img>` floods Gunicorn workers otherwise).
8. **Bot API host = `127.0.0.1:8433`** — never exposed externally. Django connects via httpx + HMAC-SHA256.
9. **TinyMCE CSRF** — read from hidden input (`{% csrf_token %}`), not cookie (cookie is HttpOnly).

### Deploy / production
10. **`deploy` user owns the git pull** for both Django and `--bot` flow (GitHub SSH key is on this user only). Do not run as root.
11. **Settings module** — `config.settings.prod` is set in `wsgi.py` and the systemd unit. `dev.py` only ever runs locally.
12. **Static / media** — Nginx serves from `/var/www/jaysonkhan/static` and `/var/www/jaysonkhan/media`.
13. **Server**: Ubuntu 24.04 at `144.91.69.225`, SSH alias `jaysonkhan`. Architecture doc: [`SERVER_ARCHITECTURE.md`](../SERVER_ARCHITECTURE.md).

### Botproxy specifics
14. **Logos** — saved to `/var/www/jaysonkhan/media/uni_logos/talabaovozi/`, served by Nginx `/media/`. Views annotate `logo_url` for direct media path (avoids Django proxy → 503 under sync workers).
15. **Bot API auth** — every call is HMAC-SHA256 via `BotAPIClient` (`apps/botproxy/client.py`) using `BOT_API_SECRET_KEY`.
16. **SiteSettings uses abstract mixins** — adding a new field group does NOT need a new model or migration of an FK; just extend the existing model with another mixin.

## Environment variables

```env
# Core
DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS
ADMIN_URL                       # admin slug
ADMIN_ALLOWED_IPS               # comma-separated whitelist

# Database
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT

# Telegram
TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_USERNAME

# Email
EMAIL_HOST EMAIL_PORT EMAIL_HOST_USER EMAIL_HOST_PASSWORD

# Bot proxy
BOT_API_BASE_URL=http://127.0.0.1:8433
BOT_API_SECRET_KEY              # MUST match hokimiyatbot's API_SECRET_KEY
BOT_API_TIMEOUT
```
