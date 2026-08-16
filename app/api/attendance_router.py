"""
==============================================================================
Apex HRMS - Advanced Attendance & Shift Management API Router
==============================================================================
"""

import re
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_request_id
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord
from app.schemas.attendance_schema import (
    ClockInRequest,
    ClockOutRequest,
    BreakRequest,
    AttendanceResponse,
    AttendanceSummaryResponse
)
from app.services.audit_service import record_audit

router = APIRouter(prefix="/attendance", tags=["Attendance & Shift Operations"])

# Standard Corporate Shift Target: 09:00 AM IST (UTC+5:30) with 15m Grace
IST_OFFSET = timezone(timedelta(hours=5, minutes=30))
SHIFT_START_MINUTES = 9 * 60          # 09:00 AM IST = 540 min
SHIFT_GRACE_MINUTES = 9 * 60 + 15     # 09:15 AM IST = 555 min


def parse_device_info(user_agent: str, client_device_info: Optional[str] = None) -> str:
    """Extract human-readable device and browser summary from User-Agent."""
    if client_device_info:
        return client_device_info.strip()

    if not user_agent:
        return "Web Browser"

    browser = "Web Browser"
    os_name = "Desktop"

    # Detect Browser
    if "Edg/" in user_agent:
        browser = "Microsoft Edge"
    elif "Chrome/" in user_agent:
        browser = "Google Chrome"
    elif "Safari/" in user_agent and "Chrome/" not in user_agent:
        browser = "Apple Safari"
    elif "Firefox/" in user_agent:
        browser = "Mozilla Firefox"

    # Detect OS / Device
    if "iPhone" in user_agent or "iPad" in user_agent:
        os_name = "iOS Device"
    elif "Android" in user_agent:
        os_name = "Android Mobile"
    elif "Windows NT 10" in user_agent:
        os_name = "Windows 10/11"
    elif "Macintosh" in user_agent or "Mac OS X" in user_agent:
        os_name = "macOS"
    elif "Linux" in user_agent:
        os_name = "Linux"

    return f"{browser} on {os_name}"


@router.post("/clock-in", response_model=AttendanceResponse)
def clock_in(
    payload: ClockInRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record employee daily shift clock-in with punctuality and device logging."""
    today = date.today()
    now_utc = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")
    device_summary = parse_device_info(user_agent, payload.device_info)

    # 1. Strict Prevention of Double Clock-In
    active_session = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == current_user.employee_id,
        AttendanceRecord.clock_out.is_(None)
    ).first()

    if active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active shift already in progress. You cannot clock in multiple times simultaneously."
        )

    # 2. Punctuality Calculation in IST
    now_ist = now_utc.astimezone(IST_OFFSET)
    current_ist_minutes = now_ist.hour * 60 + now_ist.minute

    if current_ist_minutes < SHIFT_START_MINUTES:
        punctuality_status = "EARLY"
        late_minutes = 0
    elif current_ist_minutes <= SHIFT_GRACE_MINUTES:
        punctuality_status = "ON_TIME"
        late_minutes = 0
    else:
        punctuality_status = "LATE"
        late_minutes = current_ist_minutes - SHIFT_START_MINUTES

    status_str = "LATE" if punctuality_status == "LATE" else "PRESENT"

    record = AttendanceRecord(
        employee_id=current_user.employee_id,
        work_date=today,
        clock_in=now_utc,
        scheduled_shift="General Shift (09:00 AM - 06:00 PM)",
        status=status_str,
        punctuality_status=punctuality_status,
        late_minutes=late_minutes,
        ip_address=client_ip,
        device_info=device_summary,
        notes=payload.notes
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    punct_desc = f"{punctuality_status}" if late_minutes == 0 else f"LATE by {late_minutes} mins"
    record_audit(
        db=db,
        action="ATTENDANCE_CLOCK_IN",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Clocked in at {now_ist.strftime('%I:%M:%S %p IST')} ({punct_desc}) | IP: {client_ip} | Device: {device_summary}",
        client_ip=client_ip,
        request_id=get_request_id(request)
    )

    return record.to_dict()


@router.post("/break-start", response_model=AttendanceResponse)
def start_break(
    payload: BreakRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start an active employee break during an ongoing shift."""
    now_utc = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == current_user.employee_id,
        AttendanceRecord.clock_out.is_(None)
    ).order_by(AttendanceRecord.id.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active clock-in session found. Please clock in before taking a break."
        )

    if record.is_on_break:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already on an active break session."
        )

    record.is_on_break = True
    record.break_start = now_utc
    if payload.notes:
        record.notes = f"{record.notes} | Break: {payload.notes}" if record.notes else f"Break: {payload.notes}"

    db.commit()
    db.refresh(record)

    record_audit(
        db=db,
        action="ATTENDANCE_BREAK_START",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Break started at {now_utc.strftime('%H:%M:%S UTC')}",
        client_ip=client_ip,
        request_id=get_request_id(request)
    )

    return record.to_dict()


@router.post("/break-end", response_model=AttendanceResponse)
def end_break(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume active shift and accumulate break duration."""
    now_utc = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == current_user.employee_id,
        AttendanceRecord.clock_out.is_(None)
    ).order_by(AttendanceRecord.id.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active clock-in session found."
        )

    if not record.is_on_break:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not currently on a break."
        )

    b_start = record.break_start if record.break_start.tzinfo else record.break_start.replace(tzinfo=timezone.utc)
    elapsed_break_sec = max(0, int((now_utc - b_start).total_seconds()))

    record.total_break_seconds = (record.total_break_seconds or 0) + elapsed_break_sec
    record.is_on_break = False
    record.break_start = None

    db.commit()
    db.refresh(record)

    record_audit(
        db=db,
        action="ATTENDANCE_BREAK_END",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Break ended (Duration: {elapsed_break_sec // 60}m {elapsed_break_sec % 60}s)",
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
    """Record employee clock-out, deduct breaks, and compute net working & overtime hours."""
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

    # Automatically conclude any active break before clocking out
    if record.is_on_break and record.break_start:
        b_start = record.break_start if record.break_start.tzinfo else record.break_start.replace(tzinfo=timezone.utc)
        elapsed_break_sec = max(0, int((now_utc - b_start).total_seconds()))
        record.total_break_seconds = (record.total_break_seconds or 0) + elapsed_break_sec
        record.is_on_break = False
        record.break_start = None

    record.clock_out = now_utc
    clock_in_time = record.clock_in
    if clock_in_time.tzinfo is None:
        clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)

    gross_seconds = max(0.0, (now_utc - clock_in_time).total_seconds())
    net_seconds = max(0.0, gross_seconds - (record.total_break_seconds or 0))
    net_hours = net_seconds / 3600.0
    record.total_hours = Decimal(str(round(net_hours, 2)))

    # Overtime & Shift Compliance Evaluation
    if net_hours > 8.0:
        record.overtime_hours = Decimal(str(round(net_hours - 8.0, 2)))
        record.status = "OVERTIME"
    elif net_hours < 4.5:
        record.overtime_hours = Decimal('0.00')
        record.status = "HALF_DAY"
    else:
        record.overtime_hours = Decimal('0.00')
        record.status = "PRESENT" if record.punctuality_status != "LATE" else "LATE"

    if payload.notes:
        record.notes = f"{record.notes} | Clock-out: {payload.notes}" if record.notes else payload.notes

    db.commit()
    db.refresh(record)

    ot_desc = f" | Overtime: {record.overtime_hours} hrs" if float(record.overtime_hours) > 0 else ""
    record_audit(
        db=db,
        action="ATTENDANCE_CLOCK_OUT",
        target_entity=f"Employee #{current_user.employee_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Clocked out at {now_utc.strftime('%H:%M:%S UTC')} (Net Active: {record.total_hours} hrs, Break: {(record.total_break_seconds or 0) // 60}m{ot_desc})",
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
    """Retrieve monthly attendance summary metrics, break status, and current check-in state."""
    target_eid = employee_id if employee_id and current_user.role in ["ADMIN", "MANAGER"] else current_user.employee_id

    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == target_eid
    ).all()

    total_days = len(records)
    total_hours = sum(float(r.total_hours) for r in records)
    avg_hours = round(total_hours / total_days, 1) if total_days > 0 else 0.0
    on_time_count = len([r for r in records if r.status in ["PRESENT", "OVERTIME"] or r.punctuality_status in ["ON_TIME", "EARLY"]])
    on_time_rate = round((on_time_count / total_days) * 100.0, 1) if total_days > 0 else 0.0

    today = date.today()
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
    is_on_break = bool(active_rec.is_on_break) if active_rec else False

    active_break_sec = 0
    if active_rec and active_rec.is_on_break and active_rec.break_start:
        b_start = active_rec.break_start if active_rec.break_start.tzinfo else active_rec.break_start.replace(tzinfo=timezone.utc)
        active_break_sec = max(0, int((datetime.now(timezone.utc) - b_start).total_seconds()))

    return {
        "total_days_present": total_days,
        "total_working_hours": round(total_hours, 1),
        "average_daily_hours": avg_hours,
        "on_time_rate_percent": on_time_rate,
        "is_currently_clocked_in": is_clocked_in,
        "is_on_break": is_on_break,
        "active_break_seconds": (active_rec.total_break_seconds or 0) + active_break_sec if active_rec else 0,
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
    """Live snapshot of employees currently working / on break / completed shifts today."""
    today = date.today()
    query = db.query(AttendanceRecord).join(Employee, AttendanceRecord.employee_id == Employee.eid).filter(
        AttendanceRecord.work_date == today
    )

    if current_user.role == "MANAGER":
        mgr_center = current_user.employee.ecen if current_user.employee else None
        if mgr_center and mgr_center != "Corporate HQ":
            query = query.filter(Employee.ecen == mgr_center)

    records = query.all()
    active_now = [r.to_dict() for r in records if r.clock_out is None and not r.is_on_break]
    on_break_now = [r.to_dict() for r in records if r.clock_out is None and r.is_on_break]
    completed_today = [r.to_dict() for r in records if r.clock_out is not None]

    return {
        "work_date": today.isoformat(),
        "currently_clocked_in_count": len(active_now),
        "currently_on_break_count": len(on_break_now),
        "completed_shift_count": len(completed_today),
        "active_employees": active_now,
        "on_break_employees": on_break_now,
        "completed_shifts": completed_today
    }

