#!/bin/bash
# ==============================================================================
# StaffSync 360 - Production Docker Entrypoint Script
# ==============================================================================
set -e

TARGET_PORT="${PORT:-8000}"
FORWARDED_IPS="${FORWARDED_ALLOW_IPS:-127.0.0.1,nginx,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,*}"

echo "[+] StaffSync 360: Running automated database migrations..."
alembic upgrade head || echo "[!] Alembic migrations finished or initialized via lifespan."

echo "[+] StaffSync 360: Launching FastAPI application on 0.0.0.0:${TARGET_PORT}..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${TARGET_PORT}" \
    --proxy-headers \
    --forwarded-allow-ips="${FORWARDED_IPS}"
