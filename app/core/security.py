"""
==============================================================================
StaffSync 360 - Cryptographic Security, Password Policies & Token Operations
==============================================================================
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional, Tuple
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
from app.services.cache_service import cache

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# Password Policy & Hashing
# =============================================================================

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Enforce enterprise password policy:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit (0-9)."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\\\/\[\]]", password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    return True, "Password meets security policy requirements."


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash from plain password."""
    return pwd_context.hash(password)


# =============================================================================
# JWT Access & Refresh Token Operations
# =============================================================================

def create_access_token(
    subject: Union[str, Any],
    role: str,
    session_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create short-lived signed JWT access token (15-30 mins)."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "jti": session_id or str(uuid.uuid4()),
        "exp": expire,
        "iat": now
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any],
    role: str,
    session_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str]:
    """Create long-lived signed JWT refresh token (7 days). Returns (token, session_id)."""
    now = datetime.now(timezone.utc)
    jti = session_id or str(uuid.uuid4())
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "role": role,
        "type": "refresh",
        "jti": jti,
        "exp": expire,
        "iat": now
    }
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token signature, expiration, and revocation status."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        sub = payload.get("sub")
        iat = payload.get("iat")

        # 1. Check if token JTI was individually revoked
        if jti and is_token_revoked(jti):
            return None

        # 2. Check if all sessions for user were invalidated (e.g., password change / logout all)
        if sub and iat:
            revoked_after = get_user_session_revoked_timestamp(str(sub))
            if revoked_after is not None and iat < revoked_after:
                return None

        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    """Legacy alias for decode_token."""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


# =============================================================================
# Token Revocation & Session Blacklisting
# =============================================================================

def revoke_token(jti: str, ttl_seconds: int = 86400 * 7):
    """Mark a session/token JTI as revoked in cache/store."""
    cache.set(f"revoked_token:{jti}", "1", ttl_seconds=ttl_seconds)


def is_token_revoked(jti: str) -> bool:
    """Check whether a session/token JTI has been revoked."""
    return cache.get(f"revoked_token:{jti}") is not None


def revoke_user_sessions(user_identifier: str, ttl_seconds: int = 86400 * 7):
    """Invalidate all active sessions and refresh tokens for a user (e.g. on password change)."""
    now_ts = int(datetime.now(timezone.utc).timestamp())
    cache.set(f"user_session_revocation:{user_identifier}", now_ts, ttl_seconds=ttl_seconds)


def get_user_session_revoked_timestamp(user_identifier: str) -> Optional[int]:
    """Retrieve timestamp after which all issued user tokens are invalid."""
    val = cache.get(f"user_session_revocation:{user_identifier}")
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    return None
