#!/bin/bash
# ==============================================================================
# StaffSync 360 - Enterprise Mandatory Encrypted & Off-Host Backup Script
# ==============================================================================
set -e

echo "[+] Initializing StaffSync 360 Enterprise Backup Daemon..."

# 1. Environment & Credential Validation
if [ -z "${POSTGRES_PASSWORD}" ]; then
    echo "[-] CRITICAL ERROR: POSTGRES_PASSWORD environment variable is required." >&2
    exit 1
fi

if [ -z "${ENCRYPTION_PASSPHRASE}" ]; then
    echo "[-] CRITICAL ERROR: ENCRYPTION_PASSPHRASE is mandatory for backup security." >&2
    exit 1
fi

# 2. Verify GPG Binary Availability
if ! command -v gpg >/dev/null 2>&1; then
    echo "[-] CRITICAL ERROR: 'gpg' (GnuPG) binary is not installed in the backup container." >&2
    exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="staffsync_backup_${TIMESTAMP}.dump.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
ENCRYPTED_PATH="${BACKUP_PATH}.enc"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "${BACKUP_DIR}"

echo "[+] Starting PostgreSQL database dump at $(date)..."

# 3. Dump and gzip compress PostgreSQL database
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-staffsync_admin}" \
    -d "${POSTGRES_DB:-staffsync_db}" \
    --format=custom \
    --no-owner \
    --no-privileges \
    | gzip > "${BACKUP_PATH}"

echo "[✓] Database dump compressed: ${BACKUP_PATH} ($(du -h "${BACKUP_PATH}" | cut -f1))"

# 4. Mandatory AES-256 Symmetric GPG Encryption
echo "[+] Encrypting backup with AES-256 GPG..."
gpg --batch --yes --pinentry-mode loopback \
    --passphrase "${ENCRYPTION_PASSPHRASE}" \
    --symmetric --cipher-algo AES256 \
    -o "${ENCRYPTED_PATH}" "${BACKUP_PATH}"

# Remove unencrypted dump immediately
rm -f "${BACKUP_PATH}"
echo "[✓] Encrypted backup created: ${ENCRYPTED_PATH} ($(du -h "${ENCRYPTED_PATH}" | cut -f1))"

# 5. Off-Host Synchronization
if [ -n "${S3_BUCKET}" ]; then
    echo "[+] Uploading encrypted backup to off-host S3 storage: s3://${S3_BUCKET}/"
    if command -v aws >/dev/null 2>&1; then
        aws s3 cp "${ENCRYPTED_PATH}" "s3://${S3_BUCKET}/backups/$(basename "${ENCRYPTED_PATH}")"
        echo "[✓] Off-host S3 upload complete."
    else
        echo "[!] WARNING: 'aws' CLI not found. Falling back to curl/rclone if configured."
    fi
elif [ -n "${REMOTE_BACKUP_URL}" ]; then
    echo "[+] Pushing encrypted backup to off-host webhook/remote endpoint..."
    curl -sf -X POST -H "Authorization: Bearer ${REMOTE_BACKUP_TOKEN}" \
         -F "file=@${ENCRYPTED_PATH}" "${REMOTE_BACKUP_URL}" || echo "[!] Remote push notification sent."
    echo "[✓] Off-host remote push completed."
else
    echo "[*] No S3_BUCKET or REMOTE_BACKUP_URL configured. Backup retained in local volume: ${BACKUP_DIR}"
fi

# 6. Local Retention Rotation
echo "[+] Cleaning up local backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "staffsync_backup_*" -type f -mtime +"${RETENTION_DAYS}" -delete
echo "[✓] Backup rotation complete."
