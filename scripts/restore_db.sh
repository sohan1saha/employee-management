#!/bin/bash
# ==============================================================================
# StaffSync 360 - Database Restore & Decryption Script
# ==============================================================================
set -e

BACKUP_FILE="$1"

if [ -z "${BACKUP_FILE}" ]; then
    echo "[-] Usage: $0 <path_to_backup_file.sql.gz.enc | path_to_backup_file.dump.gz>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[-] CRITICAL ERROR: Backup file '${BACKUP_FILE}' does not exist."
    exit 1
fi

if [ -z "${POSTGRES_PASSWORD}" ]; then
    echo "[-] CRITICAL ERROR: POSTGRES_PASSWORD environment variable is required."
    exit 1
fi

RESTORE_TARGET="${BACKUP_FILE}"

# 1. Decrypt if file ends with .enc
if [[ "${BACKUP_FILE}" == *.enc ]]; then
    if [ -z "${ENCRYPTION_PASSPHRASE}" ]; then
        echo "[-] CRITICAL ERROR: ENCRYPTION_PASSPHRASE is required to decrypt this backup."
        exit 1
    fi
    if ! command -v gpg >/dev/null 2>&1; then
        echo "[-] CRITICAL ERROR: 'gpg' (GnuPG) binary is not installed."
        exit 1
    fi

    DECRYPTED_PATH="/tmp/decrypted_$(basename "${BACKUP_FILE}" .enc)"
    echo "[+] Decrypting backup file using AES-256..."
    gpg --batch --yes --pinentry-mode loopback \
        --passphrase "${ENCRYPTION_PASSPHRASE}" \
        --decrypt -o "${DECRYPTED_PATH}" "${BACKUP_FILE}"
    RESTORE_TARGET="${DECRYPTED_PATH}"
fi

echo "[+] Restoring PostgreSQL database from ${RESTORE_TARGET}..."

# 2. Decompress and restore
gunzip -c "${RESTORE_TARGET}" | PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-staffsync_admin}" \
    -d "${POSTGRES_DB:-staffsync_db}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges

# 3. Clean temporary decrypted file
if [[ "${BACKUP_FILE}" == *.enc ]]; then
    rm -f "${DECRYPTED_PATH}"
fi

echo "[✓] Database successfully restored from backup."
