# jaysonkhan_v2 — CLAUDE.md

## 1. What this project is

Personal portfolio platform for a Flutter Mobile Engineer.
Production: **https://jaysonkhan.com** — 4 languages (xo/uz/ru/en), SSR-first
Django site with a small DRF API for infinite scroll, plus an admin panel
with a psutil-based server monitor + owner-only Telegram bot (Django webhook,
not polling). **Portfolio-only since 2026-05-31** — osint / botproxy /
hokimiyatbot-proxy were removed; don't resurrect them.

## 2. Tech stack

| Layer        | Technology                                               |
|--------------|----------------------------------------------------------|
| Backend      | Django 4.2 + Gunicorn (3 sync workers)                   |
| Database     | PostgreSQL                                               |
| Auth         | Email-based custom User + Telegram Login Widget (HMAC)   |
| Admin        | django-unfold (8-tab SiteSettings)                       |
| API          | DRF 3.16 + SimpleJWT                                     |
| Templates    | Django SSR + XIVA INK design system (hand-written CSS: `static/css/tokens.css` + `site.css`, NO Tailwind/node build) — law: [docs/DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md) |
| Rich text    | TinyMCE 6 (CDN) + bleach sanitizer                       |
| i18n         | django-modeltranslation (14 registered models, 4 langs, hreflang) |
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
│   │   ├── servermonitor/    psutil metrics + Telegram /status, /tariff, /logs
│   │   ├── telegram/         Telegram bot helpers / webhook glue
│   │   └── ops/              ad-hoc ops/cron utilities
│   ├── presentation/         Delivery layer
│   │   ├── api/              DRF ViewSets + Serializers (DefaultRouter)
│   │   │                     Full + lightweight "List" serializers for infinite scroll
│   │   └── web/              SSR class-based views
│   │       └── templates/web/  base.html, home, projects, blog, contact, partials
│   ├── locale/               .po/.mo (xo, uz, ru, en)
│   ├── static/               css/tokens.css + css/site.css (XIVA INK), JS, images
│   └── media/                user uploads (rich-text inline media, project covers)
├── docs/                     human docs — DESIGN-SYSTEM.md = UI qonuni;
│                             SITE-OPERATIONS.md = kontent/deploy/monitoring yuritish qo'llanmasi
├── security/
│   └── nginx/jaysonkhan.conf nginx config (kept in sync with server)
├── server-manager.sh         server health / restart helpers
├── deploy.sh                 deploy (single target: jaysonkhan Django service)
├── package.json              LEGACY Tailwind scripts — unused, no node build (XIVA INK is hand-written CSS)
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
- **XIVA INK design system (v4)** — single universal dark-ink scheme (no light/dark toggle), Schibsted Grotesk + IBM Plex Mono, terracotta/turquoise accents. ALL UI changes must follow [docs/DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md): tokens only, no new hex colors/fonts, 4-language strings. Admin uses the same scheme via `editorial.css` + `UNFOLD["THEME"]="dark"`.
- **WakaTime widget** — homepage About section reads `SiteSettings.wakatime_stats` JSON; filled by `manage.py fetch_wakatime` (env `WAKATIME_API_KEY`, cron). Empty dict → widget hidden, falls back to `about_image`.
- **v4 copy seeder** — `manage.py apply_xiva_copy` writes the approved 4-language design copy into SiteSettings (one-shot, explicit).
- **Infinite scroll** — `ProjectListSerializer` / `PostListSerializer` (lightweight) consumed by `static/js/infinite-scroll.js`.
- **Telegram auth** — Login Widget → HMAC verify with `TELEGRAM_BOT_TOKEN` → session-based `TelegramProfile`.
- **Comments / likes / reactions** — generic FK (ContentType), works on both `Post` and `Project`.
- **i18n** — 14 models registered with `django-modeltranslation` (incl. SiteSettings proxies), real per-language URLs, `hreflang` alternates, plus `Person.alternateName` (10 ism varianti) for SEO.
- **AI-bot policy** — opposite of EduStats: `robots.txt` BLOCKS AI bots here (not allow).

## 5. How to run

### Local dev

```bash
cd backend
/opt/homebrew/bin/python3.12 -m venv venv   # MUST be 3.12 (= server). Django 4.2 LTS breaks on Python 3.14: Context.__copy__ crashes every template render under the test client
source venv/bin/activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
# (default settings module = config.settings.dev)
# CSS is plain static files (XIVA INK) — no node/Tailwind build step.
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
./deploy.sh "commit message"   # push → server pull → pip → migrate → collectstatic →
                               # copy seeders → restart jaysonkhan + reload nginx →
                               # register_bot_commands → crontab block → health checks
```

- No `--bot` / `--all` flags (bot flows removed 2026-05-31); no CSS build step.
- **NON-NEGOTIABLE:** local edit → commit → `./deploy.sh` → green health checks. Never edit files on the server, never manual `ssh ... git pull`.
- deploy.sh re-runs `apply_edtech_founder_copy` + `apply_edtech_projects` on EVERY deploy — hand-edits (admin) to the SiteSettings/Project fields these seeders own are overwritten. Change the seeder command or add a data migration instead.
- deploy.sh does NOT run `compilemessages` — after editing `.po`, compile locally and **commit the `.mo`**.

### Server monitor (Telegram bot commands — owner-only)

```
/panel — control center (inline tugmalar, hammasi bir joyda)
/ip — shared admin IP allowlist (add/del/list; .env'ga TEGMAYDI)
/status  /services  /web  /ssl  /errors [h]  /disk  /top  /db
/restart (confirm bilan)  /tariff  /logs [service] [lines]  /backup
/lang — til (uz/ru)  /start  /notifications
```

- **Bot i18n (2026-07-18):** BARCHA bot matnlari `core/bot_i18n.py` katalogida
  (uz default + ru), render `t(key, lang, **fmt)`. Til: `BotChatPref` (chat_id
  keyed, `/lang` bilan o'rnatiladi) → Telegram `language_code` → uz
  (`interactions/notifications/lang.py`). Cron/alert xabarlari `owner_lang()`.
  `setMyCommands` 3 to'plam (default/uz/ru) — `register_bot_commands`
  `cmd.*` kalitlardan quradi, /start menyu ham AYNAN shu kalitlardan (drift yo'q).
  Yangi bot matni qo'shsang: kalitni katalogga (uz+ru) qo'sh, testda
  `test_every_key_has_both_languages` tekshiradi. Kanal postlari
  (channel_share.py) ataylab bir tilda — kontent, UI emas.

- **IP allowlist v2 (2026-07-18):** bot `/var/www/shared/admin_allowed_ips.json`
  (core/allowed_ips.py, atomik yozish) fayliga yozadi; jaysonkhan + uzexam +
  edustats-web admin middleware'lari har request'da shu faylni `.env` bazasiga
  UNION qiladi — restart kerak emas, `.env` o'zgarmaydi. IP qo'shish: botga
  bare IP yuborish / `/ip add` / https://jaysonkhan.com/myip/ (deep-link).
  O'chirish faqat dinamik ro'yxatga tegadi; `.env` bazaviy IP'lar bot orqali
  o'chirilmaydi (lockout himoyasi).

Backed by management commands:
```bash
python manage.py server_health_report [--quick] [--tariff] [--alert-only]
python manage.py check_cpu_alert [--threshold N]
python manage.py register_bot_commands
```

- Adding a monitored service = add a dict to `MONITORED_SERVICES` in `apps/servermonitor/metrics.py` (single source of truth; use REAL systemd unit names — `postfix@-`, `postgresql@16-main`).
- All 5 crons (check_cpu_alert, service_health_check, cron_health_check, server_health_report, monthly_log_report) run through `manage.py cron_run <target>` (writes `ops.CronRun` history). Crontab = managed marker block installed by `security/install-servermonitor-cron.sh` (deploy.sh runs it; its "4 crons" echo is stale). Never add bare crontab lines — `cron_health_check` flags them as overdue.
- Server clock is CEST/CET; Tashkent = server +3h in summer (CEST), +4h in winter (CET). Cron schedules are in server time.

## 6. Important things to keep in mind

### Architecture invariants
1. **Middleware order matters** — `RequestSanitizationMiddleware` (first) → CORS → Django Security → `SecurityHeadersMiddleware` → Session → Locale → Common → CSRF → Auth → `AdminIPRestrictionMiddleware` → Messages → `VisitorTrackingMiddleware` (LAST — acts only on final 200 HTML GET). No XFrameOptions: CSP `frame-ancestors` in Nginx handles it.
2. **CSP lives in Nginx**, not Django. New iframe embeds (YouTube etc.) require updating `frame-src` in `security/nginx/jaysonkhan.conf` AND on the server.
   - **Nginx sync tartibi (2026-07-19):** `/etc/nginx/sites-enabled/jaysonkhan` endi
     `sites-available/jaysonkhan`ga SYMLINK (oldin alohida nusxa edi — repo'dagi
     `conn_per_ip 20→60` fix serverga yetmay drift bo'lgan). Sync: repo conf →
     `sites-available/jaysonkhan` (scp+sudo cp) → `nginx -t` → `reload`. sites-enabled'ga
     to'g'ridan-to'g'ri yozish TAQIQ — symlink buziladi.
   - nginx-level 50x (rate-limit 503, gunicorn restart) uchun statik sahifalar:
     `backend/static/errors/{404,500}.html` (self-contained, collectstatic ships) +
     conf'da `location = /404.html|/500.html { root .../static/errors; internal; }`.
     Bularsiz error_page Django'ga proxy bo'lib "Not Found: /500.html" log-shovqini
     va yalang'och 404 UX berardi.
3. **Admin URL is configurable** via `ADMIN_URL` env; admin is also IP-restricted via `ADMIN_ALLOWED_IPS`.
4. **API permissions** — default `IsAdminUser`. Public endpoints (`projects`, `contact`) explicitly override with `AllowAny`.

### Common bugs to avoid
5. **NEVER use async views with Gunicorn sync workers + `@staff_member_required`** — fires "coroutine was never awaited" 500.
6. **Telegram webhook must never block** — only 3 sync Gunicorn workers (30s timeout). `interactions/notifications/webhook.py` returns 200 immediately and does the work in a daemon thread (`_dispatch_async`). Heavy work inline = dead worker + Telegram retry storm.
7. **Client IP = `HTTP_X_REAL_IP`, never `REMOTE_ADDR` or XFF** — Gunicorn binds a unix socket, so `REMOTE_ADDR` is an EMPTY string (this once 404'd the admin for everyone, whitelisted IPs included), and XFF-leftmost is client-spoofable. Reuse the fixed `_get_client_ip` in `core/security_middleware.py` / `contact/spam_protection.py` — never copy-paste a new one.
8. **Fixed-position modals in admin must be portaled to `<body>`** — the admin `.fade-in` wrapper animates `transform`, which re-roots `position:fixed` to the page div (modal renders mid-page, backdrop doesn't cover viewport). JS init: `document.body.appendChild(modal)`. Don't "fix" by removing the transform.
9. **TinyMCE CSRF** — read from hidden input (`{% csrf_token %}`), not cookie (cookie is HttpOnly).
10. **Inline `<script>` JS in templates: DOUBLE-quoted strings only** — Prettier can turn `'POST'` into curly quotes (U+2018/2019) → SyntaxError → every function in the block becomes undefined. `manage.py check` and deploy health checks stay green; only a real browser catches it. Detect: `perl -CSD -ne 'print "$.:$_" if /[\x{2018}\x{2019}]/' file.html` (stock macOS grep has no -P; without `-CSD` perl reads raw bytes and silently misses them).
11. **Multi-line template comments: `{% comment %}` only** — multi-line `{# ... #}` leaks raw text into the rendered page. Never put a literal endcomment tag inside the comment body.
12. **AJAX endpoint URL'lari FAQAT `{% url %}` orqali** — interactions (va boshqa app) URL'lari `i18n_patterns` ichida, ya'ni til-prefiksli. JS'da qo'lda yozilgan `/interactions/...` yo'l LocaleMiddleware'da 302 oladi, fetch POST'ni GET'ga aylantiradi → 405, va bu jimgina sinadi (2026-07-10 da webdan komment/reaction yuborish shu sabab buzuq edi). Template'dan data-atributda prefiksli URL uzating.
13. **Statik fayllar hashed (ManifestStaticFilesStorage, prod.py)** — nginx `/static/` ni `30d immutable` keshlaydi; hash'siz nom bilan CSS/JS o'zgarishi qaytgan mehmonga 30 kun yetib bormaydi (2026-07-12: orbit seksiyasi shu sabab "bo'sh" chiqqan). JS ichida statik yo'lni HARDCODE qilmang — template'dan `{% static %}` bilan uzating (masalan `window.XIVA_STARFIELD.portraitUrl`). Yangi statik fayl qo'shganda `git add -f` (gitignore `backend/static/*` ni yashiradi).

### Deploy / production
12. **`deploy` user owns the git pull** (GitHub SSH key is on this user only). Do not run as root.
13. **Settings module** — `config.settings.prod` is set in `wsgi.py` and the systemd unit. `dev.py` only ever runs locally.
14. **Static / media** — Nginx serves from `/var/www/jaysonkhan/static` and `/var/www/jaysonkhan/media`.
15. **Server**: Ubuntu 24.04 at `144.91.69.225`, SSH alias `jaysonkhan`. Architecture doc: [`SERVER_ARCHITECTURE.md`](../SERVER_ARCHITECTURE.md).

### i18n & copy
16. **`xo` (Khorezm dialect) is the DEFAULT locale and the owner's signature voice — NEVER edit `xo` strings or `*_xo` DB columns** when rewording/humanizing copy. Touch only uz/ru/en.
17. **Two copy systems** — `{% trans %}` strings live in `locale/*/django.po` (after editing: `compilemessages` locally + commit the `.mo`); SiteSettings modeltranslation columns change via a NEW data migration in `apps/core/migrations/` (editing an already-run seed migration does nothing).
18. **Bust the SiteSettings cache after a copy data-migration** — migrations write through historical models so `post_save` never fires; the page shows stale copy up to 5 min. On server (prod settings): `python manage.py shell -c "from django.apps import apps; S=apps.get_model('core','SiteSettings'); S.objects.get(pk=1).save()"`.

### Analytics / attribution
19. **`PageView` is a unique-visitor table (first-touch), NOT a per-pageview log** — `core.tracking.VisitorTrackingMiddleware` owns all tracking (cookie `jk_visitor` + real-IP dedup). Don't add view-level tracking; to extend sources edit `core.tracking.classify_source` (priority: utm_source > referrer host > direct) + `SOURCE_COLORS` in one place. UTM link-builder lives in admin at `core/pageview/utm-builder/`.

### SiteSettings
20. **SiteSettings uses abstract mixins** — adding a new field group does NOT need a new model or migration of an FK; just extend the existing model with another mixin. Admin "tabs" are 8 proxy models (`SiteSettingsBranding`, `...SEO`, `...Navigation`, `...Homepage`, `...Contact`, `...Telegram`, `...Emoji`, `...Editorial`).

## 7. Model selection (Claude Code)

Default = **Sonnet** — it handles everything routine here.
Switch to **Opus** ONLY for:
- **Novel architecture** — e.g. designing a servermonitor-v2-scale subsystem, a new attribution/analytics pipeline.
- **Multi-file refactors** — e.g. renaming a SiteSettings mixin across models/translations/admin/templates, or reordering security middleware.
- **Gnarly debugging** — e.g. the unix-socket empty-`REMOTE_ADDR` admin lockout, webhook worker-starvation retry storms, CSS containing-block modal traps.

Sonnet examples (the common case): add a Project field + admin column, a new XIVA INK partial, a new servermonitor bot command, `.po` copy edits.

## 8. Junior onboarding (shogird checklist)

**Reading order (mandatory, in this order):**
1. `../CLAUDE.md` (JaysonServer root) — cross-project deploy rules, server access.
2. This file.
3. [docs/DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md) — BEFORE any UI work (it is law).
4. [../SERVER_ARCHITECTURE.md](../SERVER_ARCHITECTURE.md) — for server/service questions.

**Verification gates — run and pass ALL before claiming a task done:**

```bash
backend/venv/bin/python backend/manage.py check                              # must: 0 issues
backend/venv/bin/python backend/manage.py makemigrations --check --dry-run   # must: no missing migrations
backend/venv/bin/python backend/manage.py test <touched_app> --settings=config.settings.dev
```

- Touched a template or inline JS? Render-test the page in a real browser (`runserver`) and exercise the JS — `check` passing does NOT mean the page works (see gotcha #10).
- Baseline (2026-07-02): the FULL suite is GREEN (34/34, 3.12 venv). Rule: keep it green — a task is not done if the full suite fails or the test count drops. Web-view tests must build URLs with `reverse()` (i18n prefixes: `/xo/...`), JWT auth uses `email` (USERNAME_FIELD), and Telegram notifications are auto-skipped under `manage.py test` (`fire_and_forget` guard).
- **Deploy rule (NON-NEGOTIABLE):** local edit → commit → `./deploy.sh` → all health checks green. Editing files on the server is FORBIDDEN.

## Environment variables

```env
# Core
DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS
ADMIN_URL                       # admin slug
ADMIN_ALLOWED_IPS               # comma-separated whitelist (.env base)
ADMIN_ALLOWED_IPS_FILE          # optional; default /var/www/shared/admin_allowed_ips.json
                                # (bot-managed dynamic allowlist, unioned at request time)

# Database — Django reads ONLY DATABASE_URL (env.db(); unset = sqlite db.sqlite3)
DATABASE_URL                    # prod: postgres://user:pass@localhost:5432/portfolio_db
POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD POSTGRES_HOST POSTGRES_PORT   # used ONLY by shell scripts (security/backup-db.sh, server-manager.sh)

# Telegram
TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_USERNAME

# Email
EMAIL_HOST EMAIL_PORT EMAIL_HOST_USER EMAIL_HOST_PASSWORD

# Integrations
WAKATIME_API_KEY                # fetch_wakatime cron (homepage widget)

```
