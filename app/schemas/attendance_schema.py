"""Pydantic schemas for Attendance tracking, breaks and check-in/out."""

from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class ClockInRequest(BaseModel):
    notes: Optional[str] = None
    device_info: Optional[str] = None


class ClockOutRequest(BaseModel):
    notes: Optional[str] = None


class BreakRequest(BaseModel):
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    center: Optional[str] = None
    work_date: str
    clock_in: str
    clock_out: Optional[str] = None
    break_start: Optional[str] = None
    total_break_seconds: Optional[int] = 0
    is_on_break: Optional[bool] = False
    scheduled_shift: Optional[str] = "General Shift (09:00 AM - 06:00 PM)"
    expected_hours: Optional[float] = 8.0
    elapsed_seconds: Optional[int] = None
    total_hours: float
    overtime_hours: Optional[float] = 0.0
    status: str
    punctuality_status: Optional[str] = "ON_TIME"
    late_minutes: Optional[int] = 0
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummaryResponse(BaseModel):
    total_days_present: int
    total_working_hours: float
    average_daily_hours: float
    on_time_rate_percent: float
    is_currently_clocked_in: bool
    is_on_break: Optional[bool] = False
    active_break_seconds: Optional[int] = 0
    today_record: Optional[dict] = None

