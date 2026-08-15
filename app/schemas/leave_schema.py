from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: str = Field(..., description="CASUAL, SICK, PTO, UNPAID")
    start_date: date
    end_date: date
    reason: str


class LeaveStatusUpdate(BaseModel):
    status: str = Field(..., description="APPROVED, REJECTED")
    review_comment: Optional[str] = None


class LeaveResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    center: str
    leave_type: str
    start_date: str
    end_date: str
    days_count: int
    reason: str
    status: str
    applied_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_comment: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
