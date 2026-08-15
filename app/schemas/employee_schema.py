from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EmployeeBase(BaseModel):
    eid: int = Field(..., description="Unique Employee ID")
    ename: str = Field(..., min_length=2, max_length=100, description="Employee Name")
    ecen: str = Field(..., min_length=2, max_length=60, description="Employee Center/Branch")
    epos: str = Field(..., min_length=2, max_length=80, description="Employee Position")
    esal: float = Field(..., gt=0, description="Monthly Base Salary")
    edoj: date = Field(..., description="Date of Joining (YYYY-MM-DD)")
    email: Optional[str] = None
    status: Optional[str] = "ACTIVE"


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    ename: Optional[str] = None
    ecen: Optional[str] = None
    epos: Optional[str] = None
    esal: Optional[float] = Field(None, gt=0)
    edoj: Optional[date] = None
    email: Optional[str] = None
    status: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    email: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
