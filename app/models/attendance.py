"""Attendance tracking model for daily check-in, check-out, working hours and status."""

from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.eid", ondelete="CASCADE"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, default=date.today, index=True)
    clock_in = Column(DateTime(timezone=True), nullable=False)
    clock_out = Column(DateTime(timezone=True), nullable=True)
    total_hours = Column(Numeric(5, 2), default=Decimal('0.00'), nullable=False)
    status = Column(String(30), default="PRESENT", nullable=False)  # PRESENT, HALF_DAY, LATE, OVERTIME, EARLY_DEPARTURE
    ip_address = Column(String(45), nullable=True)
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
        if self.clock_in and self.clock_out:
            cin = self.clock_in if self.clock_in.tzinfo else self.clock_in.replace(tzinfo=timezone.utc)
            cout = self.clock_out if self.clock_out.tzinfo else self.clock_out.replace(tzinfo=timezone.utc)
            elapsed_sec = max(0, int((cout - cin).total_seconds()))

        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else None,
            "center": self.employee.ecen if self.employee else None,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "clock_in": fmt_utc(self.clock_in),
            "clock_out": fmt_utc(self.clock_out),
            "elapsed_seconds": elapsed_sec,
            "total_hours": float(self.total_hours) if self.total_hours is not None else 0.0,
            "status": self.status,
            "ip_address": self.ip_address,
            "notes": self.notes,
            "created_at": fmt_utc(self.created_at)
        }

