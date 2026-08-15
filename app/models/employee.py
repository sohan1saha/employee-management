from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class Employee(Base):
    """Employee model directly evolving the original 'em1' schema:
    - eid: Employee ID (Primary Key)
    - ename: Employee Name
    - ecen: Employee Centre
    - epos: Employee Position
    - esal: Employee Salary
    - edoj: Employee Date of Joining
    Plus system timestamps and relational bindings.
    """
    __tablename__ = "employees"

    eid = Column(Integer, primary_key=True, index=True)
    ename = Column(String(100), nullable=False, index=True)
    ecen = Column(String(60), nullable=False, index=True)
    epos = Column(String(80), nullable=False)
    esal = Column(Float, nullable=False)
    edoj = Column(Date, nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, ON_LEAVE, TERMINATED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    payroll_records = relationship("PayrollRecord", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "eid": self.eid,
            "ename": self.ename,
            "ecen": self.ecen,
            "epos": self.epos,
            "esal": self.esal,
            "edoj": self.edoj.strftime("%Y-%m-%d") if self.edoj else None,
            "email": self.email,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
