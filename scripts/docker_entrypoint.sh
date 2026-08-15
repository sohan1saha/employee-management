#!/bin/bash
# ==============================================================================
# StaffSync 360 - Production Docker Entrypoint Script
# ==============================================================================
set -e

echo "[+] StaffSync 360: Running automated Alembic database migrations..."
alembic upgrade head
echo "[✓] Alembic database schema migrations completed successfully."

FORWARDED_IPS="${FORWARDED_ALLOW_IPS:-127.0.0.1,nginx,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16}"

echo "[+] StaffSync 360: Launching FastAPI application with 4 workers..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --proxy-headers \
    --forwarded-allow-ips="${FORWARDED_IPS}"
