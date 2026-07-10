> **HISTORICAL — original 2024 build spec / Codex prompt. DO NOT follow for current work.**
> The shipped reality differs: Django 4.2 (not 5), Python 3.12 on server, hand-written
> XIVA INK CSS (no Tailwind/HTMX), no `domain/` or `infrastructure/` dirs.
> Current truth: [`../CLAUDE.md`](../CLAUDE.md) + [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md).
> Kept only as project-genesis reference.

## 1?? Texnologiyalar (eng ko�p ishlatiladigan va ishonchli stack)

### Backend (Python)

* **Python 3.11**
* **Django 5 + Django REST Framework**
* **PostgreSQL** (production standart)
* **JWT Authentication (SimpleJWT)**
* **Django Admin** (admin panel)
* **Gunicorn** (WSGI)
* **Nginx** (reverse proxy)
* **Celery + Redis** (keyinchalik email / tasks uchun)
* **django-environ** (.env bilan ishlash)

### Frontend

> �frontini pythonga mos� deganing uchun:

* **Django Templates + HTMX**
* **TailwindCSS**
* Admin: **Django Admin**
* User UI: **SSR (SEO-friendly)**

?? Bu stack **portfolio, blog, projects, contact form** uchun ideal.

---

## 2?? Arxitektura (Clean Architecture ga yaqin)

Django�da **Feature-based + Clean separation**

```
backend/
+-- config/                  # project config
�   +-- settings/
�   �   +-- base.py
�   �   +-- dev.py
�   �   +-- prod.py
�   +-- urls.py
�   +-- wsgi.py
�
+-- apps/
�   +-- users/               # auth, roles
�   +-- portfolio/           # projects, skills
�   +-- blog/                # posts
�   +-- contact/             # messages
�   +-- core/                # utils, base models
�
+-- domain/                  # biznes logika
�   +-- entities/
�   +-- services/
�   +-- repositories/
�
+-- infrastructure/          # db, external services
�   +-- db/
�   +-- email/
�
+-- presentation/            # api + views
�   +-- api/
�   +-- web/
�
+-- manage.py
+-- requirements.txt
```

---

## 3?? Database (PostgreSQL)

Asosiy jadvallar:

* User (admin / user)
* Project
* Skill
* BlogPost
* ContactMessage
* SocialLinks

Hammasi **DB�da saqlanadi** ?

---

## 4?? .env.example (MUHIM)

```env
# Django
DJANGO_SECRET_KEY=change_me
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=jaysonkhan.com,www.jaysonkhan.com,144.91.69.225

# Database
POSTGRES_DB=portfolio_db
POSTGRES_USER=portfolio_user
POSTGRES_PASSWORD=strong_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# JWT
JWT_ACCESS_TOKEN_LIFETIME=5
JWT_REFRESH_TOKEN_LIFETIME=30

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=example@gmail.com
EMAIL_HOST_PASSWORD=app_password
EMAIL_USE_TLS=True

# Static & Media
STATIC_ROOT=/var/www/jaysonkhan/static
MEDIA_ROOT=/var/www/jaysonkhan/media

# Redis
REDIS_URL=redis://127.0.0.1:6379
```

---

## 5?? README.md (tayyor kontent)

````md
# Jaysonkhan Portfolio Backend

Production-ready portfolio platform with admin panel.

## Stack
- Python 3.11
- Django 5
- PostgreSQL
- Django REST Framework
- Nginx + Gunicorn

## Server
IP: 144.91.69.225  
Domain: jaysonkhan.com

---

## Installation (Ubuntu 22.04)

### 1. Serverga ulanish
```bash
ssh root@144.91.69.225
```

### 2. System dependencies

```bash
apt update && apt install -y python3 python3-venv python3-pip \
postgresql nginx redis
```

### 3. Projectni yuklash

```bash
git clone https://github.com/yourname/jaysonkhan-portfolio.git
cd backend
```

### 4. Virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. .env

```bash
cp .env.example .env
nano .env
```

### 6. Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 7. Static files

```bash
python manage.py collectstatic
```

### 8. Gunicorn

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 9. Nginx

Nginx config:

```
server {
    server_name jaysonkhan.com www.jaysonkhan.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### 10. SSL

```bash
certbot --nginx -d jaysonkhan.com -d www.jaysonkhan.com
```

---

## Admin Panel

```
/admin
```

---

## User Pages

* /
* /projects
* /blog
* /contact

````

---

## 6?? CODEx uchun ASOSIY PROMPT (eng muhim qism)

> **Buni to�liq nusxa ko�chirib Codex / Cursor / GPT ga ber**

```text
You are a senior Python backend architect.

Build a production-ready portfolio web platform using Python and Django.

Requirements:
- Domain: jaysonkhan.com
- Server IP: 144.91.69.225
- Clean Architecture principles
- PostgreSQL database
- JWT authentication
- Django Admin panel for admins
- Public website for users (portfolio, blog, contact)
- All data stored in database
- Environment variables via .env
- SSR frontend using Django Templates + TailwindCSS
- SEO friendly
- Production-ready settings (Nginx, Gunicorn)

Deliver:
- Django project structure
- Models, serializers, services, repositories
- Admin configuration
- REST API
- HTML templates
- .env.example
- requirements.txt
- README.md with server deployment steps
```