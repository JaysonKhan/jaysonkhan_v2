#!/bin/bash
# Jaysonkhan Git-based Deploy Script
# Usage: ./deploy.sh [commit message]
# Flow: git push (local) → git pull (server) → restart
#
# Runs from your Mac. Pushes code, then SSHes into the server
# to pull, install deps, build CSS, migrate, collectstatic, and restart.

set -e

# ─── Config ───────────────────────────────────────────────────────────────────
SERVER="jaysonkhan"                        # SSH alias (~/.ssh/config)
REMOTE_DIR="/var/www/jaysonkhan"           # Project root on server
BACKEND_DIR="$REMOTE_DIR/backend"          # Django backend dir
VENV="$BACKEND_DIR/venv/bin/activate"      # Virtualenv activate
PY="$BACKEND_DIR/venv/bin/python"          # Python binary
PIP="$BACKEND_DIR/venv/bin/pip"            # Pip binary
MANAGE="$BACKEND_DIR/manage.py"            # manage.py path
DEPLOY_BRANCH="main"                      # Branch to deploy on server
SERVICE="jaysonkhan"                       # systemd service name
DJANGO_SETTINGS="config.settings.prod"
DOMAIN="jaysonkhan.com"
PUBLIC_IP="144.91.69.225"

# Default commit message
MSG="${*:-deploy update}"

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}${BOLD}✔${RESET} $*"; }
warn() { echo -e "${YELLOW}${BOLD}⚠${RESET} $*"; }
err()  { echo -e "${RED}${BOLD}✖${RESET} $*"; exit 1; }
info() { echo -e "${CYAN}${BOLD}ℹ${RESET} $*"; }

# ─── Banner ───────────────────────────────────────────────────────────────────
echo
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}🚀 Jaysonkhan Deploy${RESET}  ${DIM}($DOMAIN)${RESET}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo

# ─── 1. Git add, commit, push ────────────────────────────────────────────────
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
info "1/6  Git push... (branch: $CURRENT_BRANCH)"

if [[ "$CURRENT_BRANCH" != "$DEPLOY_BRANCH" ]]; then
    warn "  You are on '$CURRENT_BRANCH', not '$DEPLOY_BRANCH'"
    warn "  Will push '$CURRENT_BRANCH' — make sure to merge into '$DEPLOY_BRANCH' for deploy!"
fi

git add -A
if git diff --cached --quiet; then
    warn "  No changes to commit — pushing anyway"
else
    git commit -m "$MSG"
    ok "  Committed: $MSG"
fi
git push origin $CURRENT_BRANCH
ok "  Pushed to origin/$CURRENT_BRANCH"
echo

# ─── 2. Server: git pull ─────────────────────────────────────────────────────
info "2/6  Server git pull (branch: $DEPLOY_BRANCH)..."
ssh $SERVER "cd $REMOTE_DIR && git pull origin $DEPLOY_BRANCH"
ok "  Code updated on server"
echo

# ─── 3. Server: Python deps ──────────────────────────────────────────────────
info "3/6  Python dependencies..."
ssh $SERVER "source $VENV && $PIP install -r $REMOTE_DIR/requirements.txt --quiet"
ok "  Dependencies installed"
echo

# ─── 4. Server: CSS build + Django migrate + collectstatic ───────────────────
info "4/6  Tailwind CSS build..."
ssh $SERVER "cd $REMOTE_DIR && \
    if command -v node >/dev/null 2>&1; then \
        npm install --silent 2>/dev/null && \
        npm run css:build 2>/dev/null && \
        echo 'CSS_OK'; \
    else \
        echo 'SKIP_CSS'; \
    fi"
echo

info "5/6  Django migrate + collectstatic..."
ssh $SERVER "source $VENV && \
    DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS $PY $MANAGE migrate --noinput && \
    DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS $PY $MANAGE collectstatic --noinput"
ok "  Migrate + collectstatic done"
echo

# ─── 5. Server: restart service ──────────────────────────────────────────────
info "6/6  Restarting services..."
ssh $SERVER "sudo systemctl daemon-reload && \
    sudo systemctl restart $SERVICE && \
    sudo systemctl reload nginx"
ok "  $SERVICE restarted, nginx reloaded"
echo

# ─── 6. Health check ─────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
info "🩺 Health check..."
sleep 3

# Try HTTPS first, then HTTP fallback
HTTPS_OK=false
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://${DOMAIN}/" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
    HTTPS_OK=true
fi

if $HTTPS_OK; then
    ok "HTTPS responds (${HTTP_CODE}): https://${DOMAIN}/"

    # Health endpoint — checks DB + cache
    HEALTH_BODY=$(curl -s --max-time 5 "https://${DOMAIN}/health/" 2>/dev/null || echo '{}')
    HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://${DOMAIN}/health/" 2>/dev/null || echo "000")
    if [[ "$HEALTH_CODE" == "200" ]]; then
        ok "Health check passed: $HEALTH_BODY"
    else
        warn "Health check returned $HEALTH_CODE: $HEALTH_BODY"
    fi

    # Check static files
    CSS_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://${DOMAIN}/static/css/output.css" 2>/dev/null || echo "000")
    if [[ "$CSS_CODE" == "200" ]]; then
        ok "Static CSS reachable"
    else
        warn "Static CSS returned $CSS_CODE (may need collectstatic or css:build)"
    fi

    echo
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${GREEN}${BOLD}✅ Deploy successful!${RESET}  https://${DOMAIN}/"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
else
    # Fallback: try IP directly
    IP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://${PUBLIC_IP}/" 2>/dev/null || echo "000")
    if [[ "$IP_CODE" =~ ^(200|301|302)$ ]]; then
        warn "HTTPS failed but HTTP on IP responds ($IP_CODE)"
        warn "Check SSL / DNS settings"
    else
        echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        err_msg="Health check failed (HTTPS: $HTTP_CODE, HTTP: $IP_CODE)"
        echo -e "${RED}${BOLD}❌ $err_msg${RESET}"
        echo
        echo -e "${DIM}Last 20 lines of service logs:${RESET}"
        ssh $SERVER "sudo journalctl -u $SERVICE -n 20 --no-pager" || true
        echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        exit 1
    fi
fi
