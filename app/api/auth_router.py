from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.user_schema import UserCreate, UserLogin, TokenResponse, UserResponse, PasswordChangeRequest
from app.api.deps import get_current_user
from app.services.audit_service import record_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    user_credentials: UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user strictly with numeric Employee ID and password."""
    user = db.query(User).filter(User.employee_id == user_credentials.employee_id).first()

    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Employee ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated"
        )

    access_token = create_access_token(
        subject=str(user.employee_id),
        role=user.role,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Set cookie for browser session persistence
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )

    # Audit login
    client_ip = request.client.host if request.client else "127.0.0.1"
    emp_name = user.employee.ename if user.employee else f"Employee #{user.employee_id}"
    record_audit(
        db=db,
        action="USER_LOGIN",
        target_entity=f"Employee #{user.employee_id} ({emp_name})",
        user_id=user.id,
        username=f"#{user.employee_id}",
        client_ip=client_ip
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allow any authenticated user (Employee, Manager, Admin) to change their password."""
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
            detail="New password and re-entered password do not match."
        )

    # 3. Verify minimum length / strength
    if len(pwd_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long."
        )

    if pwd_data.new_password == pwd_data.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as your old password."
        )

    # 4. Hash and update
    current_user.hashed_password = get_password_hash(pwd_data.new_password)
    db.commit()

    # 5. Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    record_audit(
        db=db,
        action="PASSWORD_CHANGED",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        new_value="Password successfully changed by user.",
        client_ip=client_ip
    )

    return {"message": "Password changed successfully."}


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}
