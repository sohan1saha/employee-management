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


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(UserBase):
    id: int
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
