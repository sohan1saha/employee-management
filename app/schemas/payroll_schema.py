from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PayrollGenerateRequest(BaseModel):
    month_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Billing month in format YYYY-MM")
    center: Optional[str] = None  # Optional filter by center


class PayrollApproveRequest(BaseModel):
    notes: Optional[str] = None


class PayrollResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    center: str
    position: str
    month_year: str
    base_salary: Decimal
    hra: Decimal
    allowance: Decimal
    gross_salary: Decimal
    pf_deduction: Decimal
    tax_deduction: Decimal
    net_salary: Decimal
    payment_status: str
    approved_by: Optional[int] = None
    approved_at: Optional[str] = None
    generated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
