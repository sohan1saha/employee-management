from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.leave import LeaveRequest
from app.models.employee import Employee
from app.models.user import User
from app.schemas.leave_schema import LeaveCreate, LeaveStatusUpdate, LeaveResponse
from app.api.deps import get_current_user, require_roles, get_user_scope_center
from app.services.audit_service import record_audit

router = APIRouter(prefix="/leaves", tags=["Leaves & Attendance"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_leave_request(
    leave_in: LeaveCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a new leave request."""
    # Ensure employee exists
    emp = db.query(Employee).filter(Employee.eid == leave_in.employee_id).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {leave_in.employee_id} not found"
        )

    # Calculate days count
    days = (leave_in.end_date - leave_in.start_date).days + 1
    if days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after or equal to start date."
        )

    leave_req = LeaveRequest(
        employee_id=leave_in.employee_id,
        leave_type=leave_in.leave_type,
        start_date=leave_in.start_date,
        end_date=leave_in.end_date,
        days_count=days,
        reason=leave_in.reason,
        status="PENDING"
    )
    db.add(leave_req)
    db.commit()
    db.refresh(leave_req)

    # Record Audit Log
    client_ip = request.client.host if request.client else "127.0.0.1"
    record_audit(
        db=db,
        action="LEAVE_REQUESTED",
        target_entity=f"Leave #{leave_req.id} (Emp #{emp.eid})",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        new_value=f"Type: {leave_in.leave_type}, Days: {days}, Reason: {leave_in.reason}",
        client_ip=client_ip
    )

    return leave_req.to_dict()


@router.get("", response_model=List[dict])
def list_leave_requests(
    status_filter: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List leave requests. Scoped for employees and managers."""
    query = db.query(LeaveRequest).join(Employee)

    scoped_center = get_user_scope_center(db, current_user)
    if current_user.role == "EMPLOYEE" and current_user.employee_id:
        query = query.filter(LeaveRequest.employee_id == current_user.employee_id)
    elif scoped_center:
        query = query.filter(Employee.ecen == scoped_center)

    if status_filter and status_filter != "ALL":
        query = query.filter(LeaveRequest.status == status_filter)

    leaves = query.order_by(LeaveRequest.id.desc()).all()
    return [l.to_dict() for l in leaves]


@router.patch("/{leave_id}/status")
def review_leave_request(
    leave_id: int,
    status_in: LeaveStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Approve or reject a leave request (Admin / Manager only)."""
    leave_req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave request #{leave_id} not found"
        )

    # Check manager center restriction
    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and leave_req.employee.ecen != scoped_center:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You can only review leave requests for employees in the '{scoped_center}' center."
        )

    old_status = leave_req.status
    leave_req.status = status_in.status
    leave_req.reviewed_by = current_user.id
    leave_req.review_comment = status_in.review_comment

    # If approved and leave includes today, set employee status to ON_LEAVE
    emp = db.query(Employee).filter(Employee.eid == leave_req.employee_id).first()
    if emp and status_in.status == "APPROVED":
        today = datetime.utcnow().date()
        if leave_req.start_date <= today <= leave_req.end_date:
            emp.status = "ON_LEAVE"

    db.commit()
    db.refresh(leave_req)

    # Record Audit Log
    client_ip = request.client.host if request.client else "127.0.0.1"
    record_audit(
        db=db,
        action=f"LEAVE_{status_in.status}",
        target_entity=f"Leave #{leave_id} (Emp #{leave_req.employee_id})",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        old_value=f"Status: {old_status}",
        new_value=f"Status: {status_in.status}, Comment: {status_in.review_comment or 'N/A'}",
        client_ip=client_ip
    )

    return leave_req.to_dict()
