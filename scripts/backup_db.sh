#!/bin/bash
# ==============================================================================
# StaffSync 360 - Automated Encrypted PostgreSQL Backup Script
# ==============================================================================
set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="staffsync_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "${BACKUP_DIR}"

echo "[+] Starting automated database backup at $(date)..."

# Dump and gzip compress PostgreSQL database
PGPASSWORD="${POSTGRES_PASSWORD:-staffsync_secure_pass}" pg_dump \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-staffsync_admin}" \
    -d "${POSTGRES_DB:-staffsync_db}" \
    --format=custom \
    --no-owner \
    --no-privileges \
    | gzip > "${BACKUP_PATH}"

echo "[✓] Backup created successfully: ${BACKUP_PATH} ($(du -h "${BACKUP_PATH}" | cut -f1))"

# Optional: GPG Encryption if ENCRYPTION_PASSPHRASE is supplied
if [ -n "${ENCRYPTION_PASSPHRASE}" ]; then
    echo "[+] Encrypting backup with AES-256..."
    gpg --batch --yes --passphrase "${ENCRYPTION_PASSPHRASE}" \
        --symmetric --cipher-algo AES256 -o "${BACKUP_PATH}.enc" "${BACKUP_PATH}"
    rm -f "${BACKUP_PATH}"
    echo "[✓] Encrypted backup file: ${BACKUP_PATH}.enc"
fi

# Cleanup old backups older than RETENTION_DAYS
echo "[+] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "staffsync_backup_*" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "[✓] Backup rotation complete."
