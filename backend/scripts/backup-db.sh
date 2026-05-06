#!/bin/bash
#
# SQLite daily backup script for jaysonkhan.com
#
# The site uses Django with SQLite (DATABASE_URL defaults to db.sqlite3).
# This script copies + gzips the SQLite file.
#
# Cron (daily at 2 AM, runs as root):
#   0 2 * * * /var/www/jaysonkhan/backend/scripts/backup-db.sh >> /var/log/jaysonkhan/backup.log 2>&1
#

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
PROJECT_DIR="/var/www/jaysonkhan"
SQLITE_FILE="$PROJECT_DIR/backend/db.sqlite3"
BACKUP_DIR="/var/backups/jaysonkhan"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/jaysonkhan_${TIMESTAMP}.sqlite3.gz"

# ── Backup ───────────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

if [[ ! -f "$SQLITE_FILE" ]]; then
    echo "[$(date)] ERROR: SQLite file not found: $SQLITE_FILE"
    exit 1
fi

echo "[$(date)] Starting backup of $SQLITE_FILE..."

# SQLite hot-backup: .backup pragma via sqlite3 CLI ensures consistency
# even if writers are active; gzip inline to avoid temp uncompressed copy.
if command -v sqlite3 &>/dev/null; then
    sqlite3 "$SQLITE_FILE" ".backup '${BACKUP_DIR}/tmp_backup_${TIMESTAMP}.sqlite3'" && \
        gzip -c "${BACKUP_DIR}/tmp_backup_${TIMESTAMP}.sqlite3" > "$BACKUP_FILE" && \
        rm -f "${BACKUP_DIR}/tmp_backup_${TIMESTAMP}.sqlite3"
else
    # Fallback: plain copy (safe if no writes in flight; acceptable for low-traffic site)
    gzip -c "$SQLITE_FILE" > "$BACKUP_FILE"
fi

FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup completed: $BACKUP_FILE ($FILESIZE)"

# ── Cleanup old backups ──────────────────────────────────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "jaysonkhan_*.sqlite3.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
    echo "[$(date)] Cleaned up $DELETED backup(s) older than $RETENTION_DAYS days"
fi

echo "[$(date)] Backup process finished successfully"
