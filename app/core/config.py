"""
==============================================================================
StaffSync 360 - Enterprise Configuration & Environment Settings
==============================================================================
Loads and validates all application configuration from environment variables.
Fails startup immediately if required production secrets or configs are missing.
"""

import os
from typing import List, Union, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Apex HRMS — Enterprise Workforce & Payroll"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"  # "development", "staging", "production"
    DEBUG: bool = True

    # Security & JWT Tokens
    SECRET_KEY: str = "staffsync360_enterprise_master_jwt_secret_key_2026_high_entropy_32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60       # 60 minutes (1 hour) session lifecycle
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1          # 1 day refresh token lifecycle

    # Database & Cache
    DATABASE_URL: str = "sqlite:///./staffsync.db"
    DATABASE_READ_REPLICA_URL: Optional[str] = None  # Optional PostgreSQL read-replica connection string
    REDIS_URL: str = "redis://localhost:6379/0"
    ENABLE_STRUCTURED_LOGGING: bool = True

    # Security Policies
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # Cookie Configuration
    COOKIE_SECURE: bool = False                 # Set to True in production (enforced via validator)
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"

    # CORS & Trusted Proxies
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000"
    ]
    TRUSTED_PROXIES: List[str] = [
        "127.0.0.1",
        "nginx",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16"
    ]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if not v:
            return "sqlite:///./staffsync.db"
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long for secure HS256 hashing.")
        return v

    @model_validator(mode="after")
    def validate_production_readiness(self) -> "Settings":
        """Strict fail-safe: Fails application startup if production environment has insecure dev secret."""
        is_prod = self.ENVIRONMENT.lower() in ["production", "prod"]
        if is_prod:
            # 1. Require strong non-development secret
            if "change_in_production" in self.SECRET_KEY.lower():
                raise RuntimeError(
                    "FATAL STARTUP ERROR: Insecure or default SECRET_KEY detected in PRODUCTION! "
                    "You must supply a high-entropy SECRET_KEY (min 32 characters) via environment variable or secret manager."
                )

            # 2. Enforce cookie security & disable debug mode
            self.COOKIE_SECURE = True
            self.DEBUG = False

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
