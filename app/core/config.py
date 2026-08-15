"""
==============================================================================
StaffSync 360 - Enterprise Configuration & Environment Settings
==============================================================================
Loads and validates all application configuration from environment variables.
"""

import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "StaffSync 360 - Enterprise HRMS & Payroll"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & JWT Tokens
    SECRET_KEY: str = "development_jwt_secret_key_change_in_production_staffsync360_min32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15       # 15 minutes short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7          # 7 days refresh token lifecycle

    # Database & Cache
    DATABASE_URL: str = "sqlite:///./staffsync.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security Policies
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # Cookie Configuration
    COOKIE_SECURE: bool = False                 # Set to True when HTTPS is enabled
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
    def validate_secret_key(cls, v: str, info) -> str:
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and "development" in v:
            raise ValueError(
                "CRITICAL SECURITY ERROR: Default development SECRET_KEY detected in production environment! "
                "You must provide a secure SECRET_KEY through environment variables."
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long for secure HS256 hashing.")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
