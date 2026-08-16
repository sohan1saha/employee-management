"""
==============================================================================
StaffSync 360 - Attendance & Daily Check-In/Out API Router
==============================================================================
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.deps import get_current_user, get_request_id
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord
from app.schemas.attendance_schema import ClockInRequest, ClockOutRequest, AttendanceResponse, AttendanceSummaryResponse
from app.services.audit_service import record_audit

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])


@router.post("/clock-in", response_model=AttendanceResponse)
def clock_in(
    payload: ClockInRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record employee daily clock-in."""
    today = date.today()
    now_utc = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Check if user already has an unclosed active clock-in session
    active_session = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == current_user.employee_id,
        AttendanceRecord.clock_out.is_(None)
    ).first()

    if active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are currently clocked in. Please clock out before starting a new shift."
        )

    # Determine status
    status_str = "PRESENT"

    record = AttendanceRecord(
        employee_id=current_user.employee_id,
        work_date=today,
        clock_in=now_utc,
        status=status_str,
        ip_address=client_ip,
        notes=payload.notes
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    record_audit(
        db=db,
        action="ATTENDANCE_CLOCK_IN",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Clocked in at {now_utc.strftime('%H:%M:%S UTC')} (IP: {client_ip})",
        client_ip=client_ip,
        request_id=get_request_id(request)
    )

    return record.to_dict()


@router.post("/clock-out", response_model=AttendanceResponse)
def clock_out(
    payload: ClockOutRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record employee daily clock-out and compute total working hours."""
    now_utc = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == current_user.employee_id,
        AttendanceRecord.clock_out.is_(None)
    ).order_by(AttendanceRecord.id.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active clock-in session found. Please clock in first."
        )

    record.clock_out = now_utc
    clock_in_time = record.clock_in
    if clock_in_time.tzinfo is None:
        clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = max(0.0, (now_utc - clock_in_time).total_seconds())
    hours = elapsed_seconds / 3600.0
    record.total_hours = Decimal(str(round(hours, 2)))

    if hours < 4.5:
        record.status = "HALF_DAY"
    elif hours >= 9.5:
        record.status = "OVERTIME"
    else:
        record.status = "PRESENT"

    if payload.notes:
        record.notes = f"{record.notes} | Clock-out: {payload.notes}" if record.notes else payload.notes

    db.commit()
    db.refresh(record)

    record_audit(
        db=db,
        action="ATTENDANCE_CLOCK_OUT",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Clocked out at {now_utc.strftime('%H:%M:%S UTC')} (Total: {record.total_hours} hrs)",
        client_ip=client_ip,
        request_id=get_request_id(request)
    )

    return record.to_dict()


@router.get("/summary", response_model=AttendanceSummaryResponse)
def get_attendance_summary(
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve monthly attendance summary metrics and current check-in state."""
    target_eid = employee_id if employee_id and current_user.role in ["ADMIN", "MANAGER"] else current_user.employee_id

    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == target_eid
    ).all()

    total_days = len(records)
    total_hours = sum(float(r.total_hours) for r in records)
    avg_hours = round(total_hours / total_days, 1) if total_days > 0 else 0.0
    on_time_count = len([r for r in records if r.status in ["PRESENT", "OVERTIME"]])
    on_time_rate = round((on_time_count / total_days) * 100.0, 1) if total_days > 0 else 0.0

    today = date.today()
    # Check active un-clocked-out record first
    active_rec = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == target_eid,
        AttendanceRecord.clock_out.is_(None)
    ).order_by(AttendanceRecord.id.desc()).first()

    latest_today_rec = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == target_eid,
        AttendanceRecord.work_date == today
    ).order_by(AttendanceRecord.id.desc()).first()

    today_rec = active_rec if active_rec else latest_today_rec
    is_clocked_in = active_rec is not None

    return {
        "total_days_present": total_days,
        "total_working_hours": round(total_hours, 1),
        "average_daily_hours": avg_hours,
        "on_time_rate_percent": on_time_rate,
        "is_currently_clocked_in": is_clocked_in,
        "today_record": today_rec.to_dict() if today_rec else None
    }


@router.get("/history", response_model=List[AttendanceResponse])
def get_attendance_history(
    center: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get attendance history scoped by role (Employee: self, Manager: center, Admin: all)."""
    query = db.query(AttendanceRecord).join(Employee, AttendanceRecord.employee_id == Employee.eid)

    if current_user.role == "EMPLOYEE":
        query = query.filter(AttendanceRecord.employee_id == current_user.employee_id)
    elif current_user.role == "MANAGER":
        mgr_center = current_user.employee.ecen if current_user.employee else None
        if mgr_center and mgr_center != "Corporate HQ":
            query = query.filter(Employee.ecen == mgr_center)
        elif center and center != "ALL":
            query = query.filter(Employee.ecen == center)
    elif center and center != "ALL":
        query = query.filter(Employee.ecen == center)

    offset = (page - 1) * page_size
    records = query.order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.id.desc()).offset(offset).limit(page_size).all()
    return [r.to_dict() for r in records]


@router.get("/live-status")
def get_live_team_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Live snapshot of employees currently working / checked in today."""
    today = date.today()
    query = db.query(AttendanceRecord).join(Employee, AttendanceRecord.employee_id == Employee.eid).filter(
        AttendanceRecord.work_date == today
    )

    if current_user.role == "MANAGER":
        mgr_center = current_user.employee.ecen if current_user.employee else None
        if mgr_center and mgr_center != "Corporate HQ":
            query = query.filter(Employee.ecen == mgr_center)

    records = query.all()
    active_now = [r.to_dict() for r in records if r.clock_out is None]
    completed_today = [r.to_dict() for r in records if r.clock_out is not None]

    return {
        "work_date": today.isoformat(),
        "currently_clocked_in_count": len(active_now),
        "completed_shift_count": len(completed_today),
        "active_employees": active_now,
        "completed_shifts": completed_today
    }
