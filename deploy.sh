#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Jaysonkhan Unified Deploy Script
# ══════════════════════════════════════════════════════════════════════════════
# Usage:
#   ./deploy.sh                    — deploy jaysonkhan (default)
#   ./deploy.sh "commit msg"       — deploy jaysonkhan with custom commit msg
#
# Architecture (all on jaysonkhan server 144.91.69.225):
#   /var/www/jaysonkhan/      Django admin + portfolio (systemd: jaysonkhan)

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

# ─── Parse flags ──────────────────────────────────────────────────────────────
DEPLOY_JK=false
MSG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --jk)    DEPLOY_JK=true; shift ;;
        *)       MSG="$*"; break ;;
    esac
done

# Default: deploy jaysonkhan
if ! $DEPLOY_JK; then
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
echo -e "${DIM}   Target: jaysonkhan${RESET}"
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

    # XIVA INK v4: CSS is hand-written (static/css/tokens.css + site.css),
    # no Tailwind/node build step — collectstatic ships it as-is.

    info "  Django migrate + collectstatic..."
    remote "source $JK_VENV && \
        DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE migrate --noinput && \
        DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE collectstatic --noinput"
    ok "  Migrate + collectstatic done"

    info "  Applying AI EdTech founder copy..."
    remote "source $JK_VENV && \
        DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE apply_edtech_founder_copy" \
        && ok "  AI EdTech founder copy applied" \
        || warn "  AI EdTech founder copy skipped — run manage.py apply_edtech_founder_copy manually"

    info "  Applying featured EdTech projects..."
    remote "source $JK_VENV && \
        DJANGO_SETTINGS_MODULE=$JK_SETTINGS $JK_PY $JK_MANAGE apply_edtech_projects" \
        && ok "  Featured EdTech projects applied" \
        || warn "  Featured EdTech projects skipped — run manage.py apply_edtech_projects manually"

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

    # Disable the legacy systemd timer (server_health_report) — cron_run
    # in the managed crontab block now drives the daily report and
    # records every run into ops.CronRun. Leaving the timer enabled
    # would double-fire and leave the timer's run invisible to
    # cron_health_check.
    info "  Server Monitor: disable legacy systemd timer..."
    remote "
        if systemctl list-unit-files server-health-report.timer 2>/dev/null | grep -q server-health-report.timer; then
            sudo systemctl stop server-health-report.timer 2>/dev/null || true
            sudo systemctl disable server-health-report.timer 2>/dev/null || true
            echo 'TIMER_OFF'
        else
            echo 'TIMER_ABSENT'
        fi
    " | grep -qE 'TIMER_OFF|TIMER_ABSENT' \
        && ok "  Systemd timer disabled (cron_run takes over)" \
        || warn "  Timer disable skipped"

    info "  Server Monitor: install crontab block (4 crons via cron_run)..."
    remote "bash $JK_DIR/security/install-servermonitor-cron.sh" \
        | grep -q 'CRON_OK' \
        && ok "  Crontab block installed (check_cpu_alert / service_health_check / cron_health_check / server_health_report)" \
        || warn "  Crontab install failed — inspect server crontab manually"
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
        # Server monitor crontab check — managed block must be present.
        CRON_BLOCK=$(remote "crontab -l 2>/dev/null | grep -c '^# JK_SERVERMONITOR_BEGIN$' || true")
        if [[ "$CRON_BLOCK" == "1" ]]; then
            ok "  Server monitor crontab: ${DIM}4 crons via cron_run${RESET}"
        else
            warn "  Server monitor crontab block missing — re-run deploy.sh"
        fi
    else
        echo -e "${RED}${BOLD}✖${RESET}  jaysonkhan: $JK_STATUS"
        ALL_OK=false
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
    echo -e "   ${DIM}jaysonkhan:${RESET}   $JK_SERVICE @ $JK_DIR"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
else
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${RED}${BOLD}❌ Deploy had failures${RESET}"
    echo -e "${DIM}Check: ssh $SERVER \"sudo journalctl -u <service> -f\"${RESET}"
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    exit 1
fi
