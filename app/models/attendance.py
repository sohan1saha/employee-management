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
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else None,
            "center": self.employee.ecen if self.employee else None,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "clock_in": self.clock_in.isoformat() if self.clock_in else None,
            "clock_out": self.clock_out.isoformat() if self.clock_out else None,
            "total_hours": float(self.total_hours) if self.total_hours is not None else 0.0,
            "status": self.status,
            "ip_address": self.ip_address,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
