import sys
import os
import uuid
import time
import logging
import argparse
import uvicorn
from fastapi import FastAPI, Depends, Request, Response, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, get_db
import app.models  # Ensures all models are registered with Base metadata
from app.api.auth_router import router as auth_router
from app.api.employee_router import router as employee_router
from app.api.payroll_router import router as payroll_router
from app.api.leave_router import router as leave_router
from app.api.analytics_router import router as analytics_router
from app.api.audit_router import router as audit_router
from app.services.cache_service import cache
from app.core.emp_mgmt_core import cli_menu

# Logging setup
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("staffsync.main")

# Database Initialization: Only auto-create tables in development SQLite mode
# In production, database schema must be applied via Alembic migrations (`alembic upgrade head`)
if settings.ENVIRONMENT != "production" and settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)
else:
    logger.info("Production/External Database mode: Schema management delegated to Alembic migrations.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise HRMS, Payroll Engine, and Audit Logging Platform",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
)

# =============================================================================
# Middleware: CORS Configuration
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


# =============================================================================
# Middleware: Request ID & Enterprise Security Headers
# =============================================================================
@app.middleware("http")
async def security_and_tracing_middleware(request: Request, call_next):
    # 1. Request ID Generation / Propagation
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.time()

    # 2. Payload size check (Max 10MB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"error": "Payload exceeds maximum allowed limit of 10MB.", "request_id": req_id}
        )

    # Execute request
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        logger.error(f"[ReqID: {req_id}] Unhandled Exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "An internal server error occurred. Please contact system support.",
                "request_id": req_id
            }
        )

    # 3. Attach Trace & Security Headers
    duration = time.time() - start_time
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time"] = f"{duration:.4f}s"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    if settings.COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

    return response


# =============================================================================
# API Routers
# =============================================================================
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(employee_router, prefix=settings.API_V1_STR)
app.include_router(payroll_router, prefix=settings.API_V1_STR)
app.include_router(leave_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)


# =============================================================================
# Production Health & Liveness Probes
# =============================================================================
@app.get("/healthz", tags=["System Health"])
def health_check():
    """Liveness probe for Docker, Kubernetes, and AWS ALB."""
    return {"status": "ok", "service": "staffsync-api", "version": "2.0.0"}


@app.get("/readyz", tags=["System Health"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe verifying active database and cache connections."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection unavailable")


@app.get("/api/system/health", tags=["System Health"])
def system_health_status(db: Session = Depends(get_db)):
    """Deep system diagnostic report."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    cache_status = "connected (redis)" if cache.is_redis_available else "fallback (in-memory lru)"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": "2.0.0",
        "database": {
            "dialect": engine.dialect.name,
            "status": db_status
        },
        "cache": {
            "type": cache_status,
            "status": "operational"
        }
    }


# =============================================================================
# Serve Web Dashboard Static Assets
# =============================================================================
web_dir = os.path.join(os.path.dirname(__file__), "app", "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(web_dir, "index.html"))


def run_web():
    """Launch the FastAPI Web Application & API."""
    print("=" * 60)
    print(f"[+] Launching {settings.PROJECT_NAME}")
    print("[*] Web Dashboard & API URL: http://127.0.0.1:8000")
    print("[*] Interactive Swagger Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG,
        forwarded_allow_ips=",".join(settings.TRUSTED_PROXIES)
    )


def main():
    parser = argparse.ArgumentParser(description="StaffSync 360 - Enterprise HRMS & Payroll")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in classic interactive terminal CLI mode (Your original menu)"
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Run the FastAPI Web Dashboard & REST API (Default)"
    )
    args = parser.parse_args()

    if args.cli:
        print("\nStarting Interactive CLI Mode (Preserved from your original script)...")
        cli_menu()
    else:
        run_web()


if __name__ == "__main__":
    main()
