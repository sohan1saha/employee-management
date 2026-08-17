#!/bin/bash
# ==============================================================================
# StaffSync 360 - Production Docker Entrypoint Script
# ==============================================================================
set -e

echo "[+] Apex HRMS: Starting application server..."
exec python main.py
