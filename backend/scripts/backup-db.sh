#!/bin/bash
#
# PostgreSQL daily backup script for jaysonkhan.com
#
# Usage:
#   bash /var/www/jaysonkhan/backend/scripts/backup-db.sh
#
# Cron (daily at 2 AM):
#   0 2 * * * /var/www/jaysonkhan/backend/scripts/backup-db.sh >> /var/log/jaysonkhan/backup.log 2>&1
#

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
BACKUP_DIR="/var/backups/jaysonkhan"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/jaysonkhan_${TIMESTAMP}.sql.gz"

# ── Read DB credentials from .env (grep/cut — safe with special chars) ───────
ENV_FILE="/var/www/jaysonkhan/.env"
_env() {
    grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -n1 | cut -d= -f2- | \
        sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
            -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" | tr -d '\r'
}

DB_NAME="$(_env POSTGRES_DB)"
DB_USER="$(_env POSTGRES_USER)"
DB_HOST="$(_env POSTGRES_HOST)"
DB_PORT="$(_env POSTGRES_PORT)"
POSTGRES_PASSWORD="$(_env POSTGRES_PASSWORD)"

DB_NAME="${DB_NAME:-jaysonkhan}"
DB_USER="${DB_USER:-jaysonkhan}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# ── Backup ───────────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup of database '$DB_NAME'..."

PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"

FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup completed: $BACKUP_FILE ($FILESIZE)"

# ── Cleanup old backups ──────────────────────────────────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "jaysonkhan_*.sql.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
    echo "[$(date)] Cleaned up $DELETED backup(s) older than $RETENTION_DAYS days"
fi

echo "[$(date)] Backup process finished successfully"
