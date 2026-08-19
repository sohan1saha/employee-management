from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    employee_id: int
    email: EmailStr
    role: str = "EMPLOYEE"  # ADMIN, MANAGER, EMPLOYEE
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    employee_id: int
    password: str
    remember_me: Optional[bool] = False


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in_minutes: int = 60
    session_timeout_seconds: int = 3600
    user: dict


class UserResponse(UserBase):
    id: int
    is_locked: bool = False
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
