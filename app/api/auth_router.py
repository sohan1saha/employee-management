import uuid
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    revoke_user_sessions,
    validate_password_strength
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user_schema import UserLogin, TokenResponse, PasswordChangeRequest, RefreshTokenRequest
from app.api.deps import get_current_user, get_request_id
from app.services.audit_service import record_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    user_credentials: UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user strictly with numeric Employee ID and password.
    Includes brute-force account lockout protection and issues short-lived JWTs.
    """
    now = datetime.now(timezone.utc)
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Unknown")

    user = db.query(User).filter(User.employee_id == user_credentials.employee_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Incorrect Employee ID or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account lockout status
    if user.is_locked:
        locked_time = user.locked_until
        if locked_time and locked_time.tzinfo is None:
            locked_time = locked_time.replace(tzinfo=timezone.utc)
        remaining_minutes = max(1, int((locked_time - now).total_seconds() / 60) + 1) if locked_time else 15
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account is temporarily locked due to repeated failed attempts. Please try again in {remaining_minutes} minutes.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated. Contact HR administration."
        )

    # Verify password
    if not verify_password(user_credentials.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
            db.commit()
            record_audit(
                db=db,
                action="ACCOUNT_LOCKED_BRUTE_FORCE",
                target_entity=f"Employee #{user.employee_id}",
                user_id=user.id,
                username=f"#{user.employee_id}",
                role=user.role,
                new_value=f"Locked for {settings.ACCOUNT_LOCKOUT_MINUTES} minutes after {user.failed_login_attempts} failed attempts",
                client_ip=client_ip,
                user_agent=user_agent,
                request_id=req_id
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Account is locked for {settings.ACCOUNT_LOCKOUT_MINUTES} minutes.",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Incorrect Employee ID or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failure counter on successful authentication
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    # Generate session tokens
    session_id = str(uuid.uuid4())
    access_token = create_access_token(
        subject=str(user.employee_id),
        role=user.role,
        session_id=session_id
    )
    refresh_token, _ = create_refresh_token(
        subject=str(user.employee_id),
        role=user.role,
        session_id=session_id
    )

    # Set secure HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    # Audit login
    emp_name = user.employee.ename if user.employee else f"Employee #{user.employee_id}"
    record_audit(
        db=db,
        action="USER_LOGIN",
        target_entity=f"Employee #{user.employee_id} ({emp_name})",
        user_id=user.id,
        username=f"#{user.employee_id}",
        role=user.role,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=req_id
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "user": user.to_dict()
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Exchange a valid refresh token for a fresh short-lived access token and rotated refresh token.
    Immediately revokes the previous refresh token JTI to prevent replay attacks.
    """
    token = payload.refresh_token or request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required."
        )

    decoded = decode_token(token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked refresh token. Please sign in again."
        )

    sub = decoded.get("sub")
    old_session_id = decoded.get("jti")

    # Revoke old refresh token JTI immediately
    if old_session_id:
        revoke_token(old_session_id)

    user = db.query(User).filter(User.employee_id == int(sub)).first() if sub and str(sub).isdigit() else None

    if not user or not user.is_active or user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or locked."
        )

    # Issue new rotated session tokens
    new_session_id = str(uuid.uuid4())
    new_access_token = create_access_token(
        subject=str(user.employee_id),
        role=user.role,
        session_id=new_session_id
    )
    new_refresh_token, _ = create_refresh_token(
        subject=str(user.employee_id),
        role=user.role,
        session_id=new_session_id
    )

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "user": user.to_dict()
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user profile."""
    return current_user.to_dict()


@router.post("/change-password")
def change_password(
    pwd_data: PasswordChangeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change user password with strict policy validation and session invalidation.
    """
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Unknown")

    # 1. Verify old password
    if not verify_password(pwd_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current (old) password is incorrect."
        )

    # 2. Verify new password matches confirmation
    if pwd_data.new_password != pwd_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and re-entered confirmation do not match."
        )

    # 3. Check password strength policy
    valid, err_msg = validate_password_strength(pwd_data.new_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )

    if pwd_data.new_password == pwd_data.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be identical to your old password."
        )

    # 4. Hash and update
    current_user.hashed_password = get_password_hash(pwd_data.new_password)
    db.commit()

    # 5. Invalidate all existing tokens and sessions for this user
    revoke_user_sessions(str(current_user.employee_id))

    # 6. Audit log
    record_audit(
        db=db,
        action="PASSWORD_CHANGED",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value="Password successfully changed. All active sessions and refresh tokens invalidated.",
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=req_id
    )

    return {"message": "Password changed successfully. All active sessions invalidated."}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Invalidate session cookies and revoke tokens."""
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Revoke tokens if provided
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        decoded = decode_token(token)
        if decoded and decoded.get("jti"):
            revoke_token(decoded["jti"])

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    if current_user:
        record_audit(
            db=db,
            action="USER_LOGOUT",
            target_entity=f"Employee #{current_user.employee_id}",
            user_id=current_user.id,
            username=f"#{current_user.employee_id}",
            role=current_user.role,
            client_ip=client_ip,
            request_id=req_id
        )

    return {"message": "Successfully logged out."}
