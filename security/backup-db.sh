#!/usr/bin/env bash
# ==============================================================================
# Jaysonkhan — Encrypted Database Backup Script
# Creates encrypted PostgreSQL backups with rotation
#
# Usage: Run via cron on the server
#   crontab -e
#   0 3 * * * /var/www/jaysonkhan/security/backup-db.sh >> /var/log/jaysonkhan-backup.log 2>&1
# ==============================================================================

set -Eeuo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
PROJECT_DIR="/var/www/jaysonkhan"
ENV_FILE="$PROJECT_DIR/.env"
BACKUP_DIR="/var/backups/jaysonkhan"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Read DB credentials from .env ────────────────────────────────────────────
clean_env() {
    grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | \
        sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
            -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" | tr -d '\r'
}

DB_NAME=$(clean_env POSTGRES_DB)
DB_USER=$(clean_env POSTGRES_USER)
DB_HOST=$(clean_env POSTGRES_HOST)
DB_PORT=$(clean_env POSTGRES_PORT)
DB_PASS=$(clean_env POSTGRES_PASSWORD)

# Force IPv4
[[ "$DB_HOST" == "localhost" || -z "$DB_HOST" ]] && DB_HOST="127.0.0.1"

# ── Create backup directory ──────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

DUMP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
ENCRYPTED_FILE="${DUMP_FILE}.gpg"

echo "[$(date)] Starting backup: $DB_NAME..."

# ── Create PostgreSQL dump ───────────────────────────────────────────────────
PGPASSWORD="$DB_PASS" pg_dump \
    -Fc \
    -h "$DB_HOST" \
    -p "${DB_PORT:-5432}" \
    -U "$DB_USER" \
    "$DB_NAME" \
    -f "$DUMP_FILE"

echo "[$(date)] Dump created: $DUMP_FILE ($(du -sh "$DUMP_FILE" | cut -f1))"

# ── Encrypt with GPG (symmetric, passphrase from env) ───────────────────────
BACKUP_PASSPHRASE=$(clean_env BACKUP_ENCRYPTION_KEY)
if [[ -n "$BACKUP_PASSPHRASE" ]]; then
    gpg --batch --yes --symmetric \
        --cipher-algo AES256 \
        --passphrase "$BACKUP_PASSPHRASE" \
        --output "$ENCRYPTED_FILE" \
        "$DUMP_FILE"

    # Remove unencrypted dump
    rm -f "$DUMP_FILE"
    echo "[$(date)] Encrypted backup: $ENCRYPTED_FILE"
else
    echo "[$(date)] WARNING: BACKUP_ENCRYPTION_KEY not set — backup NOT encrypted"
fi

# ── Verify backup integrity ─────────────────────────────────────────────────
FINAL_FILE="${ENCRYPTED_FILE:-$DUMP_FILE}"
if [[ -f "$FINAL_FILE" && -s "$FINAL_FILE" ]]; then
    echo "[$(date)] Backup verified: $FINAL_FILE ($(du -sh "$FINAL_FILE" | cut -f1))"
else
    echo "[$(date)] ERROR: Backup file is empty or missing!"
    exit 1
fi

# ── Rotate old backups ───────────────────────────────────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "*.dump*" -mtime +"$RETENTION_DAYS" -delete -print | wc -l)
echo "[$(date)] Rotated $DELETED old backups (>${RETENTION_DAYS} days)"

# ── Set restrictive permissions ──────────────────────────────────────────────
chmod 600 "$FINAL_FILE"
chown root:root "$FINAL_FILE"

echo "[$(date)] Backup complete ✅"
