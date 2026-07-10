# Jaysonkhan Portfolio Platform

A production-ready portfolio web platform built with Python, Django, and Clean Architecture.

> **WARNING — historical setup guide.** The production server is already provisioned and hardened.
> For day-to-day work read [`CLAUDE.md`](CLAUDE.md). Deploy ONLY via `./deploy.sh`
> (local edit -> commit -> deploy) — never re-run the manual server steps below against the live server.

## Features
- **Clean Architecture**: Separation of concerns with domain, services, and repositories.
- **REST API**: Django REST Framework endpoints for all modules.
- **SSR Frontend**: Django Templates + hand-written XIVA INK CSS for high performance and SEO.
- **JWT Authentication**: Secure API access.
- **PostgreSQL**: Production-grade database.
- **Design**: single dark-ink XIVA INK design system — see [docs/DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md).

## Tech Stack
- **Backend**: Python 3.12, Django 4.2 LTS, DRF
- **Database**: PostgreSQL (Production), SQLite (Development)
- **Frontend**: Django SSR + XIVA INK CSS (`static/css/tokens.css` + `site.css`) — no Tailwind/HTMX/node build
- **DevOps**: Gunicorn, Nginx

---

## Local Development

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd jaysonkhan_v2/backend
   ```

2. **Setup virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r ../requirements.txt
   ```

4. **Environment Variables**
   ```bash
   cp ../.env.example .env   # .env.example lives at the repo root
   # Edit .env with your local settings
   ```

5. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Start Dev Server**
   ```bash
   python manage.py runserver
   ```

---

## Server Deployment (Ubuntu 24.04 — HISTORICAL, see warning above)

**Server IP**: 144.91.69.225  
**Domain**: jaysonkhan.com

### 1. Preparation
Connect to your server:
```bash
ssh root@144.91.69.225
```

### 2. System dependencies
```bash
apt update && apt install -y python3 python3-venv python3-pip postgresql nginx redis
```

### 3. Database Setup (PostgreSQL)
```bash
sudo -u postgres psql
CREATE DATABASE portfolio_db;
CREATE USER portfolio_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE portfolio_db TO portfolio_user;
\q
```

### 4. Application Setup
```bash
git clone <repo-url> /var/www/jaysonkhan
cd /var/www/jaysonkhan/backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt gunicorn
cp .env.example .env
# Edit .env: set DJANGO_DEBUG=False, database credentials, and production paths
```

### 5. Static & Media
```bash
python manage.py collectstatic
```

### 6. Gunicorn Systemd Service
Create `/etc/systemd/system/jaysonkhan.service`:
```ini
[Unit]
Description=Gunicorn instance to serve Jaysonkhan Portfolio
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/jaysonkhan/backend
Environment="PATH=/var/www/jaysonkhan/backend/venv/bin"
ExecStart=/var/www/jaysonkhan/backend/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:jaysonkhan.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
systemctl start jaysonkhan
systemctl enable jaysonkhan
```

### 7. Nginx Configuration
Create `/etc/nginx/sites-available/jaysonkhan`:
```nginx
server {
    listen 80;
    server_name jaysonkhan.com www.jaysonkhan.com 144.91.69.225;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /var/www/jaysonkhan/static;
    }
    location /media/ {
        root /var/www/jaysonkhan/media;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/jaysonkhan/backend/jaysonkhan.sock;
    }
}
```
Link and restart Nginx:
```bash
ln -s /etc/nginx/sites-available/jaysonkhan /etc/nginx/sites-enabled
nginx -t
systemctl restart nginx
```

### 8. SSL (Certbot)
```bash
certbot --nginx -d jaysonkhan.com -d www.jaysonkhan.com
```
