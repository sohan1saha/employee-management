from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """User account model for JWT Authentication, Session Tracking & RBAC."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.eid"), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="EMPLOYEE", nullable=False)  # ADMIN, MANAGER, EMPLOYEE
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id], lazy="joined")

    @property
    def is_locked(self) -> bool:
        """Check if account is temporarily locked due to brute-force protection."""
        if self.locked_until:
            now = datetime.now(timezone.utc)
            # Handle tz-naive vs aware comparisons
            locked = self.locked_until
            if locked.tzinfo is None:
                locked = locked.replace(tzinfo=timezone.utc)
            return now < locked
        return False

    def to_dict(self):
        emp_name = self.employee.ename if self.employee else None
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "email": self.email,
            "role": self.role,
            "full_name": emp_name or f"Employee #{self.employee_id}",
            "display_name": emp_name or f"#{self.employee_id}",
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }
