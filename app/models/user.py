from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """User account model for JWT Authentication and RBAC based on Employee ID."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.eid", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="EMPLOYEE", nullable=False)  # ADMIN, MANAGER, EMPLOYEE
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id], lazy="joined")

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
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }
