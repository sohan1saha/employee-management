import uuid
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.employee import Employee

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_request_id(request: Request) -> str:
    """Extract or generate correlation request ID."""
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = str(uuid.uuid4())
    return req_id


def get_client_ip(request: Request) -> str:
    """
    Accurately extracts client IP address, respecting reverse proxies
    (Railway, Nginx, Cloudflare, AWS ALB) via X-Forwarded-For, X-Real-IP, CF-Connecting-IP.
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    xff = request.headers.get("X-Forwarded-For")
    if xff and xff.strip():
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate the currently authenticated user from Bearer Token or Cookie."""
    auth_token = token
    if not auth_token:
        auth_token = request.cookies.get("access_token")

    if not auth_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(auth_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier.",
        )

    user = None
    if str(sub).isdigit():
        user = db.query(User).filter(User.employee_id == int(sub)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account no longer exists.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated.",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account is temporarily locked due to excessive failed login attempts. Try again later.",
        )

    return user


def require_roles(allowed_roles: List[str]):
    """Decorator / dependency enforcing Role-Based Access Control (RBAC)."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role in {allowed_roles}, but your role is '{current_user.role}'."
            )
        return current_user
    return role_checker


def get_user_scope_center(db: Session, user: User) -> Optional[str]:
    """Return the center name if the user is scoped to a specific center (e.g. MANAGER)."""
    if user.role == "MANAGER" and user.employee_id:
        mgr_emp = db.query(Employee).filter(Employee.eid == user.employee_id).first()
        if mgr_emp and mgr_emp.ecen:
            return mgr_emp.ecen
    return None


def validate_resource_access(db: Session, current_user: User, target_employee_id: int) -> Employee:
    """
    Object-Level Authorization & IDOR Protection:
    Ensures that the current user is authorized to read/modify the requested employee ID.
    """
    target_emp = db.query(Employee).filter(Employee.eid == target_employee_id).first()
    if not target_emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee record #{target_employee_id} not found."
        )

    if current_user.role == "ADMIN":
        return target_emp

    if current_user.role == "MANAGER":
        scoped_center = get_user_scope_center(db, current_user)
        if scoped_center and target_emp.ecen != scoped_center:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You are only authorized to access records in the '{scoped_center}' branch."
            )
        return target_emp

    if current_user.role == "EMPLOYEE":
        if target_emp.eid != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view or manage your own personal employee records."
            )
        return target_emp

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
