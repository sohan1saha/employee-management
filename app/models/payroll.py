from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint, Index, event
from sqlalchemy.orm import relationship
from app.core.database import Base


class PayrollRecord(Base):
    """
    Payroll & Statutory Compensation Record:
    Stores high-precision monetary values with lifecycle state tracking.
    Finalized records (PAID / APPROVED) are protected against deletion at ORM level.
    """
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.eid"), nullable=False, index=True)
    month_year = Column(String(7), nullable=False, index=True)  # e.g., "2026-08"

    # Monetary components stored with 2 decimal place precision (NUMERIC(12,2))
    base_salary = Column(Numeric(12, 2), nullable=False)   # 50%
    hra = Column(Numeric(12, 2), nullable=False)           # 20%
    allowance = Column(Numeric(12, 2), nullable=False)     # 30%
    gross_salary = Column(Numeric(12, 2), nullable=False)
    pf_deduction = Column(Numeric(12, 2), nullable=False)  # 12% of basic
    tax_deduction = Column(Numeric(12, 2), nullable=False) # Progressive income tax
    net_salary = Column(Numeric(12, 2), nullable=False)

    # Lifecycle State: DRAFT -> CALCULATED -> APPROVED -> PAID
    payment_status = Column(String(20), default="DRAFT", nullable=False, index=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="payroll_records")
    approver = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        UniqueConstraint("employee_id", "month_year", name="uq_payroll_emp_month"),
        Index("ix_payroll_month_center", "month_year"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else "Unknown",
            "center": self.employee.ecen if self.employee else "N/A",
            "position": self.employee.epos if self.employee else "N/A",
            "month_year": self.month_year,
            "base_salary": float(self.base_salary) if self.base_salary is not None else 0.0,
            "hra": float(self.hra) if self.hra is not None else 0.0,
            "allowance": float(self.allowance) if self.allowance is not None else 0.0,
            "gross_salary": float(self.gross_salary) if self.gross_salary is not None else 0.0,
            "pf_deduction": float(self.pf_deduction) if self.pf_deduction is not None else 0.0,
            "tax_deduction": float(self.tax_deduction) if self.tax_deduction is not None else 0.0,
            "net_salary": float(self.net_salary) if self.net_salary is not None else 0.0,
            "payment_status": self.payment_status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.strftime("%Y-%m-%d %H:%M:%S") if self.approved_at else None,
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M:%S") if self.generated_at else None
        }


# =============================================================================
# ORM-Level Deletion Prevention for Finalized Records
# =============================================================================

def _block_finalized_payroll_delete(mapper, connection, target):
    if target.payment_status in ("PAID", "APPROVED"):
        raise PermissionError(
            f"CRITICAL FINANCIAL INTEGRITY ERROR: Payroll record #{target.id} is finalized ({target.payment_status}) "
            "and cannot be physically deleted. Financial audit records must remain immutable."
        )


event.listen(PayrollRecord, "before_delete", _block_finalized_payroll_delete)
