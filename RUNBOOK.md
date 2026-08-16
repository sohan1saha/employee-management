# 🛠️ Apex HRMS — Operations & Disaster Recovery Runbook

This runbook describes standard operating procedures (SOPs), backup/restore workflows, and security recovery playbooks for **Apex HRMS**.

---

## 📑 Table of Contents
1. [System Architecture Overview](#1-system-architecture-overview)
2. [Encrypted Backup & Disaster Recovery](#2-encrypted-backup--disaster-recovery)
3. [Zero-Downtime Deployment & CI/CD](#3-zero-downtime-deployment--cicd)
4. [Secret & Key Rotation Procedures](#4-secret--key-rotation-procedures)
5. [Cloud Observability & Health Probes](#5-cloud-observability--health-probes)

---

## 1. System Architecture Overview
* **Web & API Service:** FastAPI async ASGI backend running behind Uvicorn/Gunicorn.
* **Database Layer:** PostgreSQL 16 (or self-healing SQLite for local/edge modes) with Alembic migration versioning.
* **Cache & Blacklist:** Redis 7 (Token revocation blacklist, rate-limiting, and brute-force lockout counters).
* **Storage:** Local encrypted disk partition / AWS S3 for document compliance assets.

---

## 2. Encrypted Backup & Disaster Recovery

### Automated Backup Execution
Daily cron triggers `scripts/backup_db.sh`:
```bash
ENCRYPTION_PASSPHRASE="<Secret-GPG-Passphrase>" ./scripts/backup_db.sh
```
* Generates gzip compressed SQL snapshot.
* Applies AES-256 symmetric encryption (`.sql.gz.enc`).
* Emits SHA-256 checksum verification manifest.

### Full Disaster Recovery Restore
In the event of database failure or corrupted state:
```bash
ENCRYPTION_PASSPHRASE="<Secret-GPG-Passphrase>" ./scripts/restore_db.sh /backups/apex_backup_YYYYMMDD.sql.gz.enc
```
1. Decrypts and unpacks the compressed SQL snapshot in memory.
2. Validates schema integrity and table structures.
3. Restores records and updates atomic sequence counters.

---

## 3. Zero-Downtime Deployment & CI/CD

### Railway Production Deployments
Every push to branch `main` automatically triggers an immutable Railway build:
* **Trigger:** `git push origin main`
* **Healthcheck Path:** `/healthz` (Liveness) and `/readyz` (Readiness).
* **Production URL:** `https://web-production-767f6.up.railway.app`

### Rollback Strategy
To roll back a faulty release immediately:
```bash
git revert HEAD -m 1
git push origin main
```
Or use Railway's one-click deployment rollback to the previous green deployment hash.

---

## 4. Secret & Key Rotation Procedures

### JWT Secret Key Rotation
1. Generate high-entropy 256-bit secret key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
2. Update `SECRET_KEY` in environment variables.
3. Restart application workers. Active sessions will cleanly re-authenticate via the 7-day refresh token flow or login prompt.

---

## 5. Cloud Observability & Health Probes

| Probe / Telemetry | Endpoint | Purpose | Expected Response |
| :--- | :--- | :--- | :--- |
| **Liveness Probe** | `GET /healthz` | Kubernetes / Railway process uptime | `{"status": "ok"}` (`200 OK`) |
| **Readiness Probe**| `GET /readyz` | Verifies DB connection pool & cache connectivity | `{"status": "ready"}` (`200 OK`) |
| **Prometheus Exporter**| `GET /metrics` | OpenMetrics scraper for Grafana / Datadog | Real-time counters & latency histograms |
| **Diagnostic Health**| `GET /api/system/health` | Deep component diagnostic report | Detailed DB, cache, and disk metrics |
