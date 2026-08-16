"""Pydantic schemas for Attendance tracking and check-in/out."""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class ClockInRequest(BaseModel):
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    center: Optional[str] = None
    work_date: str
    clock_in: str
    clock_out: Optional[str] = None
    total_hours: float
    status: str
    ip_address: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummaryResponse(BaseModel):
    total_days_present: int
    total_working_hours: float
    average_daily_hours: float
    on_time_rate_percent: float
    is_currently_clocked_in: bool
    today_record: Optional[dict] = None
