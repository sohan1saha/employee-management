from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate the currently authenticated user from Bearer Token or Cookie."""
    # Check Header token first, then fallback to cookie
    auth_token = token
    if not auth_token:
        auth_token = request.cookies.get("access_token")

    if not auth_token:
        # Check Authorization header manually if needed
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
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
            detail="User account is deactivated.",
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
    """Return the center name if the user is scoped to a specific center (e.g. MANAGER).
    Returns None for unrestricted roles (e.g. ADMIN).
    """
    if user.role == "MANAGER" and user.employee_id:
        from app.models.employee import Employee
        mgr_emp = db.query(Employee).filter(Employee.eid == user.employee_id).first()
        if mgr_emp and mgr_emp.ecen:
            return mgr_emp.ecen
    return None
