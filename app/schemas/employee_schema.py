from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EmployeeBase(BaseModel):
    eid: Optional[int] = Field(None, ge=1, description="Unique Positive Employee ID (Auto-generated if omitted)")
    ename: str = Field(..., min_length=2, max_length=100, description="Employee Name")
    ecen: str = Field(..., min_length=2, max_length=60, description="Employee Center/Branch")
    epos: str = Field(..., min_length=2, max_length=80, description="Employee Position")
    esal: Decimal = Field(..., ge=0, description="Monthly Base Salary (Decimal)")
    edoj: date = Field(..., description="Date of Joining (YYYY-MM-DD)")
    email: Optional[str] = None
    status: Optional[str] = "ACTIVE"


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    ename: Optional[str] = Field(None, min_length=2, max_length=100)
    ecen: Optional[str] = Field(None, min_length=2, max_length=60)
    epos: Optional[str] = Field(None, min_length=2, max_length=80)
    esal: Optional[Decimal] = Field(None, ge=0)
    edoj: Optional[date] = None
    email: Optional[str] = None
    status: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    eid: int
    email: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
