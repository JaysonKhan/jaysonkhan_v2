#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Jaysonkhan Unified Deploy Script
# ══════════════════════════════════════════════════════════════════════════════
# Usage:
#   ./deploy.sh                    — deploy jaysonkhan only (default)
#   ./deploy.sh --all              — deploy jaysonkhan + talabaovozi
#   ./deploy.sh --bot              — deploy talabaovozi bot only
#   ./deploy.sh --bot "fix bug"    — deploy bot with custom commit message
#   ./deploy.sh "commit msg"       — deploy jaysonkhan with custom commit msg
#
# Architecture (all on jaysonkhan server 144.91.69.225):
#   /var/www/jaysonkhan/      Django admin + portfolio (systemd: jaysonkhan)
#   /var/www/talabaovozi/     Telegram bot + API       (systemd: talabaovozi)
#   Bot API: 127.0.0.1:8433 (localhost only, not exposed)

set -e

# ─── Config ───────────────────────────────────────────────────────────────────
SERVER="jaysonkhan"
DOMAIN="jaysonkhan.com"
PUBLIC_IP="144.91.69.225"

# Django config
JK_DIR="/var/www/jaysonkhan"
JK_BACKEND="$JK_DIR/backend"
JK_VENV="$JK_BACKEND/venv/bin/activate"
JK_PY="$JK_BACKEND/venv/bin/python"
JK_PIP="$JK_BACKEND/venv/bin/pip"
JK_MANAGE="$JK_BACKEND/manage.py"
JK_BRANCH="main"
JK_SERVICE="jaysonkhan"
JK_SETTINGS="config.settings.prod"

# Bot config
BOT_DIR="/var/www/talabaovozi"
BOT_VENV="$BOT_DIR/venv/bin/activate"
BOT_PIP="$BOT_DIR/venv/bin/pip"
BOT_BRANCH="ovoz_v2"
BOT_SERVICE="talabaovozi"

# ─── Parse flags ──────────────────────────────────────────────────────────────
DEPLOY_JK=false
DEPLOY_BOT=false
MSG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)   DEPLOY_JK=true; DEPLOY_BOT=true; shift ;;
        --bot)   DEPLOY_BOT=true; shift ;;
        --jk)    DEPLOY_JK=true; shift ;;
        *)       MSG="$*"; break ;;
    esac
done

# Default: deploy jaysonkhan if no flag specified
if ! $DEPLOY_JK && ! $DEPLOY_BOT; then
    DEPLOY_JK=true
fi
MSG="${MSG:-deploy update}"

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

remote() { ssh "$SERVER" "$@"; }

START_TIME=$(date +%s)

# ─── Banner ───────────────────────────────────────────────────────────────────
echo
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}🚀 Jaysonkhan Deploy${RESET}  ${DIM}($DOMAIN)${RESET}"
echo -e "${DIM}   $(date '+%Y-%m-%d %H:%M:%S')${RESET}"
TARGETS=""
$DEPLOY_JK && TARGETS+="jaysonkhan "
$DEPLOY_BOT && TARGETS+="talabaovozi "
echo -e "${DIM}   Targets: ${TARGETS}${RESET}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo

# ─── Pre-flight ───────────────────────────────────────────────────────────────
info "Pre-flight checks..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SERVER" "echo ok" &>/dev/null; then
    err "Cannot connect to server '$SERVER'. Check SSH config."
fi
ok "  SSH connection OK"
echo

# ─── Git push (current repo) ─────────────────────────────────────────────────
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
info "Git push... ${DIM}(branch: $CURRENT_BRANCH)${RESET}"

git add -A
if git diff --cached --quiet; then
    warn "  No changes to commit — pushing anyway"
else
    git commit -m "$MSG"
    ok "  Committed: ${DIM}$MSG${RESET}"
fi
git push origin "$CURRENT_BRANCH"
ok "  Pushed to origin/$CURRENT_BRANCH"
echo

ALL_OK=true

# ══════════════════════════════════════════════════════════════════════════════
# Deploy jaysonkhan (Django)
# ══════════════════════════════════════════════════════════════════════════════
if $DEPLOY_JK; then
    echo -e "${CYAN}${BOLD}── jaysonkhan (Django) ──${RESET}"

    info "  Server git pull..."
    remote "cd $JK_DIR && git pull origin $JK_BRANCH"
    ok "  Code updated"

    info "  Python dependencies..."
    remote "source $JK_VENV && $JK_PIP install -r $JK_DIR/requirements.txt --quiet"
    ok "  Dependencies installed"

    info "  Tailwind CSS build..."
    remote "cd $JK_DIR && \
        if command -v node >/dev/null 2>&1; then \
            npm install --silent 2>/dev/null && \
            npm run css:build 2>/dev/null && \
            echo 'CSS_OK'; \
        else \
            echo 'SKIP_CSS'; \
        fi"

    info "  Django migrate + collectstatic..."
    remote "source $JK_VENV && \
        DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE migrate --noinput && \
        DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE collectstatic --noinput"
    ok "  Migrate + collectstatic done"

    info "  Restarting jaysonkhan + nginx..."
    remote "sudo systemctl daemon-reload && \
        sudo systemctl restart $JK_SERVICE && \
        sudo systemctl reload nginx"
    ok "  $JK_SERVICE restarted"

    # ── Server Monitor setup ─────────────────────────────────────────────────
    info "  Server Monitor: register bot commands..."
    remote "source $JK_VENV && \
        DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE register_bot_commands 2>/dev/null" \
        && ok "  Bot commands registered" \
        || warn "  Bot commands registration skipped"

    info "  Server Monitor: systemd timer..."
    remote "
        # Copy timer files if they don't exist or are outdated
        sudo cp $JK_BACKEND/apps/servermonitor/systemd/server-health-report.service /etc/systemd/system/ 2>/dev/null && \
        sudo cp $JK_BACKEND/apps/servermonitor/systemd/server-health-report.timer /etc/systemd/system/ 2>/dev/null && \
        sudo systemctl daemon-reload && \
        sudo systemctl enable server-health-report.timer 2>/dev/null && \
        sudo systemctl start server-health-report.timer 2>/dev/null && \
        echo 'TIMER_OK' || echo 'TIMER_SKIP'
    " | grep -q 'TIMER_OK' \
        && ok "  Daily health report timer enabled (09:00)" \
        || warn "  Timer setup skipped (may already be active)"

    info "  Server Monitor: CPU alert cron..."
    remote "
        CRON_LINE='*/10 * * * * source $JK_VENV && DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE check_cpu_alert 2>/dev/null'
        (crontab -l 2>/dev/null | grep -v 'check_cpu_alert'; echo \"\$CRON_LINE\") | crontab -
        echo 'CRON_OK'
    " | grep -q 'CRON_OK' \
        && ok "  CPU alert cron installed (every 10 min)" \
        || warn "  CPU alert cron setup skipped"
    echo
fi

# ══════════════════════════════════════════════════════════════════════════════
# Deploy talabaovozi (Bot)
# ══════════════════════════════════════════════════════════════════════════════
if $DEPLOY_BOT; then
    echo -e "${CYAN}${BOLD}── talabaovozi (Bot) ──${RESET}"

    info "  Server git pull..."
    # Use deploy user (not sudo/root) for git operations — deploy key is on deploy user
    remote "ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null || true"
    REMOTE_BEFORE=$(remote "git -C $BOT_DIR rev-parse --short HEAD 2>/dev/null" || echo "?")
    remote "git -C $BOT_DIR fetch origin $BOT_BRANCH && \
        git -C $BOT_DIR checkout $BOT_BRANCH 2>/dev/null; \
        git -C $BOT_DIR reset --hard origin/$BOT_BRANCH"
    remote "find $BOT_DIR -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true"
    REMOTE_AFTER=$(remote "sudo git -C $BOT_DIR rev-parse --short HEAD 2>/dev/null" || echo "?")
    ok "  Code updated: ${DIM}$REMOTE_BEFORE → $REMOTE_AFTER${RESET}"

    info "  Python dependencies..."
    DEPS_OUTPUT=$(remote "sudo bash -c 'source $BOT_VENV && $BOT_PIP install -r $BOT_DIR/requirements.txt --quiet 2>&1'" || true)
    if echo "$DEPS_OUTPUT" | grep -qi "error\|failed"; then
        warn "  Dependency install had warnings"
    else
        ok "  Dependencies installed"
    fi

    info "  Restarting talabaovozi..."
    remote "sudo systemctl daemon-reload && sudo systemctl restart $BOT_SERVICE"
    ok "  $BOT_SERVICE restarted"
    echo
fi

# ─── Health checks ────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
info "Health checks..."
sleep 3

if $DEPLOY_JK; then
    JK_STATUS=$(remote "sudo systemctl is-active $JK_SERVICE 2>/dev/null" || echo "unknown")
    if [[ "$JK_STATUS" == "active" ]]; then
        ok "  jaysonkhan: active"
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://${DOMAIN}/" 2>/dev/null || echo "000")
        if [[ "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
            ok "  HTTPS: ${DIM}$HTTP_CODE${RESET}"
        else
            warn "  HTTPS returned $HTTP_CODE"
        fi
        HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://${DOMAIN}/health/" 2>/dev/null || echo "000")
        if [[ "$HEALTH_CODE" == "200" ]]; then
            ok "  Health endpoint: OK"
        else
            warn "  Health endpoint: $HEALTH_CODE"
        fi
        # Server monitor timer check
        TIMER_STATUS=$(remote "sudo systemctl is-active server-health-report.timer 2>/dev/null" || echo "unknown")
        if [[ "$TIMER_STATUS" == "active" ]]; then
            NEXT_RUN=$(remote "sudo systemctl show server-health-report.timer --property=NextElapseUSecRealtime --value 2>/dev/null" || echo "")
            ok "  Health report timer: active ${DIM}(next: $NEXT_RUN)${RESET}"
        else
            warn "  Health report timer: $TIMER_STATUS"
        fi
    else
        echo -e "${RED}${BOLD}✖${RESET}  jaysonkhan: $JK_STATUS"
        ALL_OK=false
    fi
fi

if $DEPLOY_BOT; then
    BOT_STATUS=$(remote "sudo systemctl is-active $BOT_SERVICE 2>/dev/null" || echo "unknown")
    if [[ "$BOT_STATUS" == "active" ]]; then
        ok "  talabaovozi: active"
        API_HEALTH=$(remote "curl -sf --max-time 3 http://127.0.0.1:8433/api/v1/health 2>/dev/null" || echo "unavailable")
        if [[ "$API_HEALTH" != "unavailable" ]]; then
            ok "  Bot API: ${DIM}$API_HEALTH${RESET}"
        else
            warn "  Bot API health check failed (may still be starting)"
        fi
        # Check port not exposed externally
        EXT_CHECK=$(curl -sf --max-time 3 "http://${PUBLIC_IP}:8433/" 2>/dev/null && echo "EXPOSED" || echo "SAFE")
        if [[ "$EXT_CHECK" == "SAFE" ]]; then
            ok "  Port 8433: ${DIM}not exposed externally${RESET}"
        else
            warn "  Port 8433 is accessible externally! Check firewall."
        fi
    else
        echo -e "${RED}${BOLD}✖${RESET}  talabaovozi: $BOT_STATUS"
        ALL_OK=false
        remote "sudo journalctl -u $BOT_SERVICE -n 15 --no-pager" 2>/dev/null || true
    fi
fi

# ─── Final status ─────────────────────────────────────────────────────────────
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_STR="${DURATION}s"
[[ "$DURATION" -ge 60 ]] && DURATION_STR="$((DURATION / 60))m $((DURATION % 60))s"

echo
if $ALL_OK; then
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${GREEN}${BOLD}✅ Deploy successful!${RESET}  ${DIM}(${DURATION_STR})${RESET}"
    $DEPLOY_JK  && echo -e "   ${DIM}jaysonkhan:${RESET}   $JK_SERVICE @ $JK_DIR"
    $DEPLOY_BOT && echo -e "   ${DIM}talabaovozi:${RESET}  $BOT_SERVICE @ $BOT_DIR"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
else
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${RED}${BOLD}❌ Deploy had failures${RESET}"
    echo -e "${DIM}Check: ssh $SERVER \"sudo journalctl -u <service> -f\"${RESET}"
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    exit 1
fi
