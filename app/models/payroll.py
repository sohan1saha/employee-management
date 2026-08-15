from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class PayrollRecord(Base):
    """Payroll and Compensation record."""
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.eid", ondelete="CASCADE"), nullable=False, index=True)
    month_year = Column(String(7), nullable=False, index=True)  # e.g., "2026-08"
    base_salary = Column(Float, nullable=False)  # 50%
    hra = Column(Float, nullable=False)          # 20%
    allowance = Column(Float, nullable=False)    # 30%
    gross_salary = Column(Float, nullable=False)
    pf_deduction = Column(Float, nullable=False) # 12% of basic
    tax_deduction = Column(Float, nullable=False)# income tax / prof tax
    net_salary = Column(Float, nullable=False)
    payment_status = Column(String(20), default="PAID", nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="payroll_records")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else "Unknown",
            "center": self.employee.ecen if self.employee else "N/A",
            "position": self.employee.epos if self.employee else "N/A",
            "month_year": self.month_year,
            "base_salary": round(self.base_salary, 2),
            "hra": round(self.hra, 2),
            "allowance": round(self.allowance, 2),
            "gross_salary": round(self.gross_salary, 2),
            "pf_deduction": round(self.pf_deduction, 2),
            "tax_deduction": round(self.tax_deduction, 2),
            "net_salary": round(self.net_salary, 2),
            "payment_status": self.payment_status,
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M:%S") if self.generated_at else None
        }
