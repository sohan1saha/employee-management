"""
Tests for Remember Me option, 1-Hour Session Lifecycle, and Token Expiration Guards.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.config import settings
from app.core.security import decode_token

client = TestClient(app)


def test_login_1_hour_session_expiration():
    """Verify login issues a 60-minute (1-hour) access token and session metadata."""
    res = client.post("/api/auth/login", json={
        "employee_id": 9924101,
        "password": "admin123",
        "remember_me": True
    })
    assert res.status_code == 200
    data = res.json()
    
    # 1. Assert session window metadata is 60 minutes / 3600 seconds
    assert data["expires_in_minutes"] == 60
    assert data["session_timeout_seconds"] == 3600
    assert "access_token" in data
    
    # 2. Decode JWT access token and verify exp - iat is exactly 3600 seconds (1 hour)
    token = data["access_token"]
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "9924101"
    assert decoded["role"] == "ADMIN"
    
    iat = decoded["iat"]
    exp = decoded["exp"]
    duration_seconds = exp - iat
    assert duration_seconds == 3600, f"Expected 3600s (1 hr) expiration, got {duration_seconds}s"


def test_login_remember_me_flag_handling():
    """Verify login supports optional remember_me parameter."""
    # Test with remember_me = False
    res_false = client.post("/api/auth/login", json={
        "employee_id": 9924101,
        "password": "admin123",
        "remember_me": False
    })
    assert res_false.status_code == 200
    assert res_false.json()["expires_in_minutes"] == 60

    # Test without remember_me (defaults to False in schema)
    res_default = client.post("/api/auth/login", json={
        "employee_id": 9924101,
        "password": "admin123"
    })
    assert res_default.status_code == 200
    assert res_default.json()["expires_in_minutes"] == 60


def test_cookie_max_age_1_hour():
    """Verify HTTP-only cookie headers set max_age to 3600 seconds."""
    res = client.post("/api/auth/login", json={
        "employee_id": 9924101,
        "password": "admin123"
    })
    assert res.status_code == 200
    
    set_cookie_headers = res.headers.get_list("set-cookie")
    access_cookie = next((c for c in set_cookie_headers if "access_token=" in c), None)
    assert access_cookie is not None
    assert "Max-Age=3600" in access_cookie or "max-age=3600" in access_cookie.lower()
