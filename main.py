import sys
import os
import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Ensures all models are registered with Base metadata
from app.api.auth_router import router as auth_router
from app.api.employee_router import router as employee_router
from app.api.payroll_router import router as payroll_router
from app.api.leave_router import router as leave_router
from app.api.analytics_router import router as analytics_router
from app.api.audit_router import router as audit_router
from app.core.emp_mgmt_core import cli_menu

# Auto-create all tables in SQLite/configured database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise HRMS, Payroll Engine, and Audit Logging Platform",
    version="1.0.0"
)

# CORS middleware for open development access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(employee_router, prefix=settings.API_V1_STR)
app.include_router(payroll_router, prefix=settings.API_V1_STR)
app.include_router(leave_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)

# Serve Web Dashboard static assets
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
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


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
