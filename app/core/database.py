"""
==============================================================================
StaffSync 360 - Database Engine & Connection Pool Manager
==============================================================================
Configures high-concurrency connection pooling for PostgreSQL clusters
with read-replica query routing and safe fallback for SQLite test environments.
"""

from typing import Dict, Any, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

import logging

logger = logging.getLogger("staffsync.database")

# 1. Primary Master Engine Configuration (Writes & Core Transactions)
try:
    if settings.DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
    else:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True
        )
except Exception as e:
    logger.error(f"Failed to initialize master database engine: {e}. Falling back to SQLite fallback.")
    engine = create_engine(
        "sqlite:///./staffsync.db",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Read-Replica Engine Configuration (Read-Heavy Queries / Analytics)
if settings.DATABASE_READ_REPLICA_URL and not settings.DATABASE_READ_REPLICA_URL.startswith("sqlite"):
    read_engine = create_engine(
        settings.DATABASE_READ_REPLICA_URL,
        pool_size=30,
        max_overflow=15,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True
    )
    ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)
else:
    read_engine = engine
    ReadSessionLocal = SessionLocal

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for primary database session management (Writes & Core Transactions)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for read-replica database session management (Analytics & Read Operations)."""
    db = ReadSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pool_status() -> Dict[str, Any]:
    """Retrieve connection pool metrics for Prometheus observability."""
    try:
        pool = engine.pool
        return {
            "size": pool.size() if hasattr(pool, "size") else 1,
            "checkedin": pool.checkedin() if hasattr(pool, "checkedin") else 1,
            "checkedout": pool.checkedout() if hasattr(pool, "checkedout") else 0,
            "overflow": pool.overflow() if hasattr(pool, "overflow") else 0
        }
    except Exception:
        return {"size": 1, "checkedin": 1, "checkedout": 0, "overflow": 0}
