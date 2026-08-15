from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class LeaveRequest(Base):
    """Leave & Attendance tracking request model."""
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.eid", ondelete="CASCADE"), nullable=False, index=True)
    leave_type = Column(String(30), nullable=False)  # SICK, CASUAL, PTO, MATERNITY, UNPAID
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_count = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_comment = Column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="leave_requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else "Unknown",
            "center": self.employee.ecen if self.employee else "N/A",
            "leave_type": self.leave_type,
            "start_date": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "end_date": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "days_count": self.days_count,
            "reason": self.reason,
            "status": self.status,
            "reviewed_by": (self.reviewer.employee.ename if (self.reviewer and self.reviewer.employee) else (f"#{self.reviewer.employee_id}" if self.reviewer else None)),
            "review_comment": self.review_comment
        }
