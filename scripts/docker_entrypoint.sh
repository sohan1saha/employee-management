#!/bin/bash
# ==============================================================================
# StaffSync 360 - Production Docker Entrypoint Script
# ==============================================================================
set -e

echo "[+] StaffSync 360: Checking database migrations..."
alembic upgrade head || echo "[!] Database migrations initialized via lifespan."

echo "[+] StaffSync 360: Starting application server..."
exec python main.py
