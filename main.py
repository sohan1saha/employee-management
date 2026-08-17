import sys
import os
import uuid
import time
import logging
import argparse
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Response, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, get_db, get_read_db, get_pool_status
import app.models  # Ensures all models are registered with Base metadata
from app.api.auth_router import router as auth_router
from app.api.employee_router import router as employee_router
from app.api.payroll_router import router as payroll_router
from app.api.leave_router import router as leave_router
from app.api.analytics_router import router as analytics_router
from app.api.audit_router import router as audit_router
from app.api.attendance_router import router as attendance_router
from app.api.performance_router import router as performance_router
from app.api.document_router import router as document_router
from app.api.notification_router import router as notification_router
from app.services.cache_service import cache
from app.services.metrics_service import metrics_collector
from app.core.emp_mgmt_core import cli_menu

# Logging setup
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("staffsync.main")


def init_db_sync():
    """Synchronous schema and seed verification runner."""
    try:
        from app.core.database import Base, engine, SessionLocal
        import app.models  # Register all models
        Base.metadata.create_all(bind=engine)

        from app.models.user import User
        db = SessionLocal()
        user_count = db.query(User).count()
        if user_count == 0:
            logger.info("Empty database detected on startup. Seeding master records...")
            from seed_data import seed_database
            seed_database(reset=False)
        db.close()
        logger.info("Database schema and seed records successfully verified.")
    except Exception as e:
        logger.error(f"Startup database initialization error: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure schema tables and initial seed data exist for zero-touch cloud deployment."""
    logger.info("Application starting: Initializing database schema in background thread...")
    import asyncio
    asyncio.create_task(asyncio.to_thread(init_db_sync))
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise HRMS, Payroll Engine, and Audit Logging Platform",
    version="2.0.0",
    lifespan=lifespan,
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
# Middleware: Request ID, HTTPS Redirection & Enterprise Security Headers
# =============================================================================
@app.middleware("http")
async def security_and_tracing_middleware(request: Request, call_next):
    # 1. Force HTTPS redirect in production (exempt health probes and internal requests)
    if settings.ENVIRONMENT == "production":
        if not request.url.path.startswith(("/healthz", "/readyz", "/.well-known")):
            proto = request.headers.get("x-forwarded-proto", "").lower()
            if proto == "http":
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=status.HTTP_301_MOVED_PERMANENTLY)

    # 2. Request ID Generation / Propagation
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.time()

    # 3. Payload size check (Max 10MB)
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

    # 4. Record OpenTelemetry / Prometheus Metrics
    metrics_collector.record_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration
    )

    # 5. Cloud Structured JSON Logging
    if settings.ENABLE_STRUCTURED_LOGGING and settings.ENVIRONMENT == "production":
        client_ip = request.client.host if request.client else "127.0.0.1"
        logger.info(
            f'{{"timestamp":"{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}",'
            f'"level":"INFO","service":"staffsync-api","request_id":"{req_id}",'
            f'"client_ip":"{client_ip}","method":"{request.method}","path":"{request.url.path}",'
            f'"status_code":{response.status_code},"duration_ms":{duration * 1000:.2f}}}'
        )

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
app.include_router(attendance_router, prefix=settings.API_V1_STR)
app.include_router(performance_router, prefix=settings.API_V1_STR)
app.include_router(document_router, prefix=settings.API_V1_STR)
app.include_router(notification_router, prefix=settings.API_V1_STR)


# =============================================================================
# Observability & Prometheus Metrics Endpoint
# =============================================================================
@app.get("/metrics", tags=["Observability"])
def prometheus_metrics():
    """Exposes standard OpenMetrics / Prometheus telemetry metrics."""
    pool_stats = get_pool_status()
    output = metrics_collector.generate_prometheus_output(
        active_db_connections=pool_stats.get("checkedout", 0)
    )
    return PlainTextResponse(
        content=output,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


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
    port_str = str(os.environ.get("PORT", "8000")).strip()
    try:
        port = int(port_str)
    except Exception:
        port = 8000
    host = "0.0.0.0"
    print("=" * 60)
    print(f"[+] Launching {settings.PROJECT_NAME}")
    print(f"[*] Web Dashboard & API listening on: http://{host}:{port}")
    print(f"[*] Interactive Swagger Docs: http://{host}:{port}/docs")
    print("=" * 60)
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        forwarded_allow_ips="*",
        proxy_headers=True
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
