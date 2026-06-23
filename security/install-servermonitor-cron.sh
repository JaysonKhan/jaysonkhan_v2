#!/usr/bin/env bash
# Idempotent installer for the Server Monitor cron block.
#
# Replaces (or inserts) the block delimited by the markers
#   # JK_SERVERMONITOR_BEGIN ... # JK_SERVERMONITOR_END
# in the *current user's* crontab. Also strips legacy direct-call lines
# for any of the five monitored commands so we never end up with both
# a wrapped and an unwrapped scheduled run.
#
# Run on the deploy user — it owns the relevant crontab.
#   bash /var/www/jaysonkhan/security/install-servermonitor-cron.sh
#
# Env overrides (sane defaults baked in):
#   PROJECT_DIR  /var/www/jaysonkhan
#   PYTHON       $PROJECT_DIR/backend/venv/bin/python
#   MANAGE       $PROJECT_DIR/backend/manage.py
#   LOG          /var/log/jaysonkhan/cron.log
#   DJ_SETTINGS  config.settings.prod

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/var/www/jaysonkhan}"
PYTHON="${PYTHON:-$PROJECT_DIR/backend/venv/bin/python}"
MANAGE="${MANAGE:-$PROJECT_DIR/backend/manage.py}"
LOG="${LOG:-/var/log/jaysonkhan/cron.log}"
DJ_SETTINGS="${DJ_SETTINGS:-config.settings.prod}"

BEGIN='# JK_SERVERMONITOR_BEGIN'
END='# JK_SERVERMONITOR_END'

NEW_BLOCK=$(cat <<EOF
$BEGIN
# Managed by deploy.sh — do not edit manually
# Staggered: no job fires at :00 (avoids thundering-herd CPU spike when
# UzExam hourly jobs also start at :00, causing all-cores-100% burst).
# service_health_check runs every 2 min (odd minutes, never :00) for
# near-real-time DOWN/UP alerts — cheap now that the check batches its
# systemctl probes into 2 calls (~0.06s).
3,13,23,33,43,53 * * * * cd $PROJECT_DIR/backend && DJANGO_SETTINGS_MODULE=$DJ_SETTINGS $PYTHON $MANAGE cron_run check_cpu_alert >> $LOG 2>&1
1-59/2 * * * * cd $PROJECT_DIR/backend && DJANGO_SETTINGS_MODULE=$DJ_SETTINGS $PYTHON $MANAGE cron_run service_health_check >> $LOG 2>&1
2 * * * *    cd $PROJECT_DIR/backend && DJANGO_SETTINGS_MODULE=$DJ_SETTINGS $PYTHON $MANAGE cron_run cron_health_check >> $LOG 2>&1
0 9 * * *    cd $PROJECT_DIR/backend && DJANGO_SETTINGS_MODULE=$DJ_SETTINGS $PYTHON $MANAGE cron_run server_health_report >> $LOG 2>&1
5 0 1 * *    cd $PROJECT_DIR/backend && DJANGO_SETTINGS_MODULE=$DJ_SETTINGS $PYTHON $MANAGE cron_run monthly_log_report >> $LOG 2>&1
$END
EOF
)

EXISTING=$(crontab -l 2>/dev/null || true)

# Strip the old marker block (if any) and any legacy bare-command lines
# for the five monitored crons, so we start from a clean slate.
CLEANED=$(printf '%s\n' "$EXISTING" | awk -v B="$BEGIN" -v E="$END" '
    $0 == B { skip = 1; next }
    $0 == E { skip = 0; next }
    !skip   { print }
' | grep -vE 'check_cpu_alert|service_health_check|cron_health_check|server_health_report|monthly_log_report' || true)

# Re-emit: cleaned crontab, blank separator, fresh managed block.
{
    if [ -n "$CLEANED" ]; then
        printf '%s\n' "$CLEANED"
    fi
    printf '%s\n' "$NEW_BLOCK"
} | crontab -

echo "CRON_OK"
