from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, CheckConstraint, Index, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Employee(Base):
    """
    Master Employee Model:
    - eid: Employee ID (Primary Key)
    - ename: Employee Name
    - ecen: Employee Centre
    - epos: Employee Position
    - esal: Employee Salary (Decimal/Numeric(12,2))
    - edoj: Employee Date of Joining
    - status: ACTIVE | ON_LEAVE | TERMINATED
    """
    __tablename__ = "employees"

    eid = Column(Integer, primary_key=True, index=True)
    ename = Column(String(100), nullable=False, index=True)
    ecen = Column(String(60), nullable=False, index=True)
    epos = Column(String(80), nullable=False)
    esal = Column(Numeric(12, 2), nullable=False)
    edoj = Column(Date, nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    status = Column(String(20), default="ACTIVE", nullable=False, index=True)  # ACTIVE, ON_LEAVE, TERMINATED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships (Preserves historical records upon termination)
    payroll_records = relationship("PayrollRecord", back_populates="employee", lazy="select")
    leave_requests = relationship("LeaveRequest", back_populates="employee", lazy="select")

    __table_args__ = (
        CheckConstraint("esal >= 0", name="chk_employee_salary_positive"),
        Index("ix_emp_center_status", "ecen", "status"),
    )

    def to_dict(self):
        return {
            "eid": self.eid,
            "ename": self.ename,
            "ecen": self.ecen,
            "epos": self.epos,
            "esal": float(self.esal) if self.esal is not None else 0.0,
            "edoj": self.edoj.strftime("%Y-%m-%d") if self.edoj else None,
            "email": self.email,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
