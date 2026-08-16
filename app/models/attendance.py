"""Attendance tracking model for daily check-in, check-out, break times, working hours and status."""

from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.eid", ondelete="CASCADE"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, default=date.today, index=True)
    clock_in = Column(DateTime(timezone=True), nullable=False)
    clock_out = Column(DateTime(timezone=True), nullable=True)

    # Break time management
    break_start = Column(DateTime(timezone=True), nullable=True)
    total_break_seconds = Column(Integer, default=0, nullable=False)
    is_on_break = Column(Boolean, default=False, nullable=False)

    # Shift, Hours & Overtime
    scheduled_shift = Column(String(100), default="General Shift (09:00 AM - 06:00 PM)", nullable=False)
    total_hours = Column(Numeric(5, 2), default=Decimal('0.00'), nullable=False)
    overtime_hours = Column(Numeric(5, 2), default=Decimal('0.00'), nullable=False)

    # Punctuality & Status
    status = Column(String(30), default="PRESENT", nullable=False)  # PRESENT, HALF_DAY, LATE, OVERTIME, EARLY_DEPARTURE
    punctuality_status = Column(String(30), default="ON_TIME", nullable=False)  # ON_TIME, EARLY, LATE
    late_minutes = Column(Integer, default=0, nullable=False)

    # Audit, Device & Location Metadata
    ip_address = Column(String(45), nullable=True)
    device_info = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", backref="attendance_records")

    def to_dict(self) -> dict:
        def fmt_utc(dt: datetime | None) -> str | None:
            if not dt:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        elapsed_sec = None
        if self.clock_in:
            cin = self.clock_in if self.clock_in.tzinfo else self.clock_in.replace(tzinfo=timezone.utc)
            end_time = (self.clock_out if self.clock_out.tzinfo else self.clock_out.replace(tzinfo=timezone.utc)) if self.clock_out else datetime.now(timezone.utc)
            raw_sec = max(0, int((end_time - cin).total_seconds()))

            # Account for active ongoing break if currently on break
            active_break_sec = 0
            if self.is_on_break and self.break_start:
                b_start = self.break_start if self.break_start.tzinfo else self.break_start.replace(tzinfo=timezone.utc)
                active_break_sec = max(0, int((datetime.now(timezone.utc) - b_start).total_seconds()))

            effective_break_sec = (self.total_break_seconds or 0) + active_break_sec
            elapsed_sec = max(0, raw_sec - effective_break_sec)

        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else None,
            "center": self.employee.ecen if self.employee else None,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "clock_in": fmt_utc(self.clock_in),
            "clock_out": fmt_utc(self.clock_out),
            "break_start": fmt_utc(self.break_start),
            "total_break_seconds": self.total_break_seconds or 0,
            "is_on_break": bool(self.is_on_break),
            "scheduled_shift": self.scheduled_shift or "General Shift (09:00 AM - 06:00 PM)",
            "expected_hours": 8.0,
            "elapsed_seconds": elapsed_sec,
            "total_hours": float(self.total_hours) if self.total_hours is not None else 0.0,
            "overtime_hours": float(self.overtime_hours) if self.overtime_hours is not None else 0.0,
            "status": self.status,
            "punctuality_status": self.punctuality_status or "ON_TIME",
            "late_minutes": self.late_minutes or 0,
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "notes": self.notes,
            "created_at": fmt_utc(self.created_at)
        }


