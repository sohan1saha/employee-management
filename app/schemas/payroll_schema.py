from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PayrollGenerateRequest(BaseModel):
    month_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Billing month in format YYYY-MM")
    center: Optional[str] = None  # Optional filter by center


class PayrollResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    center: str
    position: str
    month_year: str
    base_salary: float
    hra: float
    allowance: float
    gross_salary: float
    pf_deduction: float
    tax_deduction: float
    net_salary: float
    payment_status: str
    generated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
