#!/bin/bash
# ==============================================================================
# StaffSync 360 - Production Docker Entrypoint Script
# ==============================================================================
set -e

# Database migrations are automatically verified via application lifespan
# alembic upgrade head || true
echo "[+] Apex HRMS: Starting application server..."
exec python main.py
