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

# Load env vars (DB credentials)
ENV_FILE="/var/www/jaysonkhan/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

DB_NAME="${POSTGRES_DB:-jaysonkhan}"
DB_USER="${POSTGRES_USER:-jaysonkhan}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

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
