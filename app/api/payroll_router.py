from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.payroll import PayrollRecord
from app.models.employee import Employee
from app.models.user import User
from app.schemas.payroll_schema import PayrollGenerateRequest, PayrollResponse
from app.api.deps import get_current_user, require_roles, get_user_scope_center
from app.services.payroll_service import generate_payroll_for_month, generate_payslip_pdf
from app.services.cache_service import cache

router = APIRouter(prefix="/payroll", tags=["Payroll & Compensation"])


@router.post("/generate", response_model=List[dict])
def trigger_payroll_generation(
    payload: PayrollGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"]))
):
    """Trigger payroll calculation and record generation for all active employees (Admin only)."""
    user_dict = {"id": current_user.id, "employee_id": current_user.employee_id, "username": f"#{current_user.employee_id}"}
    records = generate_payroll_for_month(
        db=db,
        month_year=payload.month_year,
        center=payload.center,
        current_user=user_dict
    )
    cache.invalidate_prefix("analytics:")
    return [r.to_dict() for r in records]


@router.get("", response_model=List[dict])
def list_payroll_records(
    month_year: Optional[str] = Query(None, description="Filter by month-year e.g. 2026-08"),
    center: Optional[str] = Query(None, description="Filter by center"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List payroll records. Scoped for employees and managers."""
    query = db.query(PayrollRecord).join(Employee)

    # Restrict standard employee to their own records
    if current_user.role == "EMPLOYEE" and current_user.employee_id:
        query = query.filter(PayrollRecord.employee_id == current_user.employee_id)
    else:
        # Check manager center restriction
        scoped_center = get_user_scope_center(db, current_user)
        if scoped_center:
            query = query.filter(Employee.ecen == scoped_center)
        elif center and center != "ALL":
            query = query.filter(Employee.ecen == center)

    if month_year:
        query = query.filter(PayrollRecord.month_year == month_year)

    records = query.order_by(PayrollRecord.id.desc()).all()
    return [r.to_dict() for r in records]


@router.get("/payslip/{record_id}/pdf")
def download_payslip_pdf(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download styled PDF payslip for an individual payroll record."""
    record = db.query(PayrollRecord).filter(PayrollRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )

    # Permission check: If employee role, ensure this record belongs to them
    if current_user.role == "EMPLOYEE" and current_user.employee_id != record.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are only authorized to view your own payslips."
        )

    # Permission check: If manager, ensure employee belongs to their center
    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and record.employee.ecen != scoped_center:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You can only view payslips for employees in the '{scoped_center}' center."
        )

    pdf_buffer = generate_payslip_pdf(record)
    filename = f"Payslip_{record.employee.ename.replace(' ', '_')}_{record.month_year}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
