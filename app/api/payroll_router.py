from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.payroll import PayrollRecord
from app.models.employee import Employee
from app.models.user import User
from app.schemas.payroll_schema import PayrollGenerateRequest, PayrollApproveRequest
from app.api.deps import get_current_user, require_roles, get_user_scope_center, get_request_id
from app.services.payroll_service import generate_payroll_for_month, generate_payslip_pdf
from app.services.audit_service import record_audit
from app.services.cache_service import cache

router = APIRouter(prefix="/payroll", tags=["Payroll & Compensation"])

VALID_TRANSITIONS = {
    "DRAFT": ["CALCULATED"],
    "CALCULATED": ["APPROVED", "PAID"],
    "APPROVED": ["PAID"],
    "PAID": []  # Terminal state (Immutable)
}


@router.post("/generate", response_model=List[dict])
def trigger_payroll_generation(
    payload: PayrollGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"]))
):
    """Trigger batch payroll calculation with Decimal precision (Admin only)."""
    user_dict = {
        "id": current_user.id,
        "employee_id": current_user.employee_id,
        "username": f"#{current_user.employee_id}",
        "role": current_user.role
    }
    records = generate_payroll_for_month(
        db=db,
        month_year=payload.month_year,
        center=payload.center,
        current_user=user_dict
    )
    cache.invalidate_prefix("analytics:")
    return [r.to_dict() for r in records]


@router.post("/{record_id}/approve")
def approve_payroll_record(
    record_id: int,
    approve_data: Optional[PayrollApproveRequest],
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Formally approve a calculated payroll record."""
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Unknown")

    record = db.query(PayrollRecord).filter(PayrollRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found."
        )

    # State Machine Check
    if record.payment_status not in ["DRAFT", "CALCULATED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition. Cannot approve record already in '{record.payment_status}' status."
        )

    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and record.employee.ecen != scoped_center:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You can only approve payroll for employees in the '{scoped_center}' branch."
        )

    old_status = record.payment_status
    record.payment_status = "APPROVED"
    record.approved_by = current_user.id
    record.approved_at = datetime.now(timezone.utc)
    db.commit()

    record_audit(
        db=db,
        action="PAYROLL_APPROVED",
        target_entity=f"Payroll #{record.id} (Emp #{record.employee_id})",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        old_value=f"Status: {old_status}",
        new_value=f"Status: APPROVED, Approver: #{current_user.employee_id}, Amount: ₹{record.net_salary}",
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=req_id
    )

    return {"message": f"Payroll record #{record_id} approved and finalized.", "record": record.to_dict()}


@router.post("/{record_id}/disburse")
def disburse_payroll_record(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"]))
):
    """Mark an approved payroll record as PAID (Disbursed)."""
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Unknown")

    record = db.query(PayrollRecord).filter(PayrollRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found."
        )

    if record.payment_status not in ["APPROVED", "CALCULATED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition. Cannot disburse payroll in '{record.payment_status}' status."
        )

    record.payment_status = "PAID"
    db.commit()

    record_audit(
        db=db,
        action="PAYROLL_DISBURSED",
        target_entity=f"Payroll #{record.id} (Emp #{record.employee_id})",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Status: PAID, Amount: ₹{record.net_salary}",
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=req_id
    )

    return {"message": f"Payroll record #{record_id} marked as PAID.", "record": record.to_dict()}


@router.get("", response_model=List[dict])
def list_payroll_records(
    month_year: Optional[str] = Query(None, description="Filter by month-year e.g. 2026-08"),
    center: Optional[str] = Query(None, description="Filter by center"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List payroll records with multi-center scoping and pagination."""
    query = db.query(PayrollRecord).join(Employee)

    if current_user.role == "EMPLOYEE" and current_user.employee_id:
        query = query.filter(PayrollRecord.employee_id == current_user.employee_id)
    else:
        scoped_center = get_user_scope_center(db, current_user)
        if scoped_center:
            query = query.filter(Employee.ecen == scoped_center)
        elif center and center != "ALL":
            query = query.filter(Employee.ecen == center)

    if month_year:
        query = query.filter(PayrollRecord.month_year == month_year)

    offset = (page - 1) * page_size
    records = query.order_by(PayrollRecord.id.desc()).offset(offset).limit(page_size).all()
    return [r.to_dict() for r in records]


@router.get("/payslip/{record_id}/pdf")
def download_payslip_pdf(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download styled PDF payslip with strict IDOR verification."""
    record = db.query(PayrollRecord).filter(PayrollRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found."
        )

    # IDOR Check: Employee can only view their own payslip
    if current_user.role == "EMPLOYEE" and current_user.employee_id != record.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are only authorized to view your own payslips."
        )

    # IDOR Check: Manager can only view payslips for their center
    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and record.employee.ecen != scoped_center:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You can only view payslips for employees in the '{scoped_center}' center."
        )

    pdf_buffer = generate_payslip_pdf(record)
    safe_name = (record.employee.ename or "Employee").replace(" ", "_")
    filename = f"Payslip_{safe_name}_{record.month_year}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
