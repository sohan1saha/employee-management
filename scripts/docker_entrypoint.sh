#!/bin/bash
# ==============================================================================
# StaffSync 360 - Production Docker Entrypoint Script
# ==============================================================================
set -e

TARGET_PORT="${PORT:-8000}"
export FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"

echo "[+] StaffSync 360: Starting application server on 0.0.0.0:${TARGET_PORT}..."
exec python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "${TARGET_PORT}" \
    --proxy-headers \
    --forwarded-allow-ips="*"
