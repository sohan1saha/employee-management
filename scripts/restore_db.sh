#!/bin/bash
# ==============================================================================
# StaffSync 360 - Database Restore Utility
# ==============================================================================
set -e

BACKUP_FILE="$1"

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    exit 1
fi

if [ -z "${POSTGRES_PASSWORD}" ]; then
    echo "[-] CRITICAL ERROR: POSTGRES_PASSWORD environment variable is required."
    exit 1
fi

echo "[!] WARNING: This will restore and overwrite the database from ${BACKUP_FILE}."
echo "[+] Starting database restore at $(date)..."

# Decrypt if .enc
TEMP_FILE="${BACKUP_FILE}"
if [[ "${BACKUP_FILE}" == *.enc ]]; then
    if [ -z "${ENCRYPTION_PASSPHRASE}" ]; then
        echo "[-] Error: ENCRYPTION_PASSPHRASE required to decrypt ${BACKUP_FILE}"
        exit 1
    fi
    TEMP_FILE="/tmp/restore_decrypted.sql.gz"
    gpg --batch --yes --passphrase "${ENCRYPTION_PASSPHRASE}" \
        --decrypt -o "${TEMP_FILE}" "${BACKUP_FILE}"
fi

# Restore PostgreSQL database
gunzip -c "${TEMP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-staffsync_admin}" \
    -d "${POSTGRES_DB:-staffsync_db}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges

if [ "${TEMP_FILE}" != "${BACKUP_FILE}" ]; then
    rm -f "${TEMP_FILE}"
fi

echo "[✓] Database restored successfully from ${BACKUP_FILE}!"
