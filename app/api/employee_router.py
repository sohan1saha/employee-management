from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.employee import Employee
from app.models.user import User
from app.models.sequence import EmployeeSequence
from app.schemas.employee_schema import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.api.deps import get_current_user, require_roles, get_user_scope_center, validate_resource_access, get_request_id
from app.services.audit_service import record_audit
from app.services.cache_service import cache

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=List[dict])
def list_employees(
    search: Optional[str] = Query(None, description="Search by name, ID, or position"),
    center: Optional[str] = Query(None, description="Filter by center/branch"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ON_LEAVE, TERMINATED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve list of employees with multi-center scoping and pagination.
    Employees see only themselves; managers only their assigned center.
    """
    query = db.query(Employee)

    if current_user.role == "EMPLOYEE" and current_user.employee_id:
        query = query.filter(Employee.eid == current_user.employee_id)
    else:
        scoped_center = get_user_scope_center(db, current_user)
        if scoped_center:
            query = query.filter(Employee.ecen == scoped_center)
        elif center and center != "ALL":
            query = query.filter(Employee.ecen == center)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Employee.ename.ilike(search_pattern),
                Employee.epos.ilike(search_pattern),
                Employee.ecen.ilike(search_pattern),
                Employee.eid.like(search_pattern)
            )
        )

    if status and status != "ALL":
        query = query.filter(Employee.status == status)
    elif not status:
        # Default behavior: Exclude TERMINATED employees unless status="ALL" or status="TERMINATED" is explicitly provided
        query = query.filter(Employee.status != "TERMINATED")

    offset = (page - 1) * page_size
    employees = query.order_by(Employee.eid.asc()).offset(offset).limit(page_size).all()
    return [emp.to_dict() for emp in employees]


CENTER_CODES = {
    "central": "99",
    "corporate": "99",
    "corporate hq": "99",
    "hq": "99",
    "admin": "99",
    "bangalore": "10",
    "bengaluru": "10",
    "delhi": "20",
    "mumbai": "30",
    "kolkata": "40",
    "hyderabad": "50",
    "chennai": "60",
    "pune": "70",
    "noida": "80",
    "gurugram": "90"
}


def get_center_code(center_name: str) -> str:
    """Return 2-digit center code from center name."""
    if not center_name:
        return "10"
    normalized = center_name.strip().lower()
    if normalized in CENTER_CODES:
        return CENTER_CODES[normalized]
    return str(10 + (abs(hash(normalized)) % 89))


import threading

_id_allocation_lock = threading.Lock()


def get_next_recommended_employee_id(db: Session, center: str, doj_str: Optional[str] = None) -> int:
    """
    Generate next recommended continuous Employee ID following pattern:
    [Center Code (2 digits)][Year of Joining (2 digits)][Sequential Main ID (3+ digits)]
    Uses atomic sequence partition locking (EmployeeSequence + threading.Lock) to guarantee zero collisions under concurrency.
    """
    with _id_allocation_lock:
        now = datetime.now(timezone.utc)
        year_code = str(now.year)[-2:]
        if doj_str:
            try:
                year_val = datetime.strptime(doj_str[:10], "%Y-%m-%d").year
                year_code = str(year_val)[-2:]
            except Exception:
                pass

        center_code = get_center_code(center)
        prefix_str = f"{center_code}{year_code}"
        prefix_num = int(prefix_str)

        min_range = prefix_num * 1000 + 100
        max_range = prefix_num * 1000 + 999

        highest_eid = db.query(func.max(Employee.eid)).filter(
            Employee.eid >= min_range,
            Employee.eid <= max_range
        ).scalar()

        highest_seq_in_table = (highest_eid % 1000) if highest_eid else 100

        seq_rec = db.query(EmployeeSequence).filter(EmployeeSequence.prefix == prefix_str).with_for_update().first()

        if not seq_rec:
            initial_seq = max(100, highest_seq_in_table) + 1
            seq_rec = EmployeeSequence(prefix=prefix_str, last_sequence=initial_seq)
            db.add(seq_rec)
            db.commit()
            return prefix_num * 1000 + initial_seq
        else:
            next_seq = max(seq_rec.last_sequence, highest_seq_in_table) + 1
            seq_rec.last_sequence = next_seq
            db.commit()
            return prefix_num * 1000 + next_seq


@router.get("/next-id")
def get_next_id(
    center: str = Query(..., description="Employee Center name e.g. Bangalore, Delhi"),
    doj: Optional[str] = Query(None, description="Date of Joining (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Retrieve auto-recommended continuous Employee ID."""
    scoped_center = get_user_scope_center(db, current_user)
    selected_center = scoped_center if scoped_center else center

    recommended_id = get_next_recommended_employee_id(db, selected_center, doj)
    center_code = get_center_code(selected_center)
    return {
        "next_id": recommended_id,
        "center": selected_center,
        "center_code": center_code,
        "pattern": f"{center_code} + YY + Sequence"
    }


@router.get("/centers/list")
def get_centers_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return distinct centers available to user."""
    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center:
        return [scoped_center]

    centers = db.query(Employee.ecen).distinct().all()
    results = sorted(list(set([c[0] for c in centers if c[0]])))
    if not results:
        results = ["Bangalore", "Delhi", "Mumbai", "Kolkata"]
    return results


@router.get("/{eid}", response_model=dict)
def get_employee(
    eid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve individual employee record with IDOR verification."""
    emp = validate_resource_access(db, current_user, eid)
    return emp.to_dict()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_employee(
    emp_in: EmployeeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Create a new employee record with input validation and audit logging."""
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Unknown")

    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and emp_in.ecen != scoped_center:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. As manager of '{scoped_center}', you can only add employees to your center."
        )

    allocated_id = emp_in.eid
    if not allocated_id:
        allocated_id = get_next_recommended_employee_id(db, emp_in.ecen, str(emp_in.edoj))

    # Check if ID already exists
    existing = db.query(Employee).filter(Employee.eid == allocated_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee with ID {allocated_id} already exists!"
        )

    email = emp_in.email or f"emp{allocated_id}@staffsync.internal"
    existing_email = db.query(Employee).filter(Employee.email == email).first()
    if existing_email:
        email = f"emp{allocated_id}_{emp_in.ename.lower().replace(' ', '')}@staffsync.internal"

    employee = Employee(
        eid=allocated_id,
        ename=emp_in.ename,
        ecen=emp_in.ecen,
        epos=emp_in.epos,
        esal=emp_in.esal,
        edoj=emp_in.edoj,
        email=email,
        status=emp_in.status or "ACTIVE"
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    # Auto-provision login account for the employee with specified or inferred role
    role_to_set = "EMPLOYEE"
    if emp_in.system_role:
        role_to_set = emp_in.system_role.upper()
    elif "manager" in emp_in.epos.lower():
        role_to_set = "MANAGER"

    existing_user = db.query(User).filter(User.employee_id == employee.eid).first()
    if not existing_user:
        raw_pwd = emp_in.initial_password or ("manager123" if role_to_set == "MANAGER" else "employee123")
        new_user = User(
            email=employee.email,
            hashed_password=get_password_hash(raw_pwd),
            role=role_to_set,
            employee_id=employee.eid,
            is_active=True
        )
        db.add(new_user)
        db.commit()
    elif emp_in.system_role and current_user.role == "ADMIN":
        existing_user.role = role_to_set
        db.commit()

    record_audit(
        db=db,
        action="EMPLOYEE_CREATED",
        target_entity=f"Employee #{employee.eid}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Name: {employee.ename}, Center: {employee.ecen}, Pos: {employee.epos}, Role: {role_to_set}, Sal: ₹{employee.esal}",
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=req_id
    )

    cache.invalidate_prefix("analytics")
    return employee.to_dict()


@router.put("/{eid}")
def update_employee(
    eid: int,
    emp_in: EmployeeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Update employee details with field authorization and audit logging."""
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Unknown")

    emp = validate_resource_access(db, current_user, eid)

    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center:
        if emp_in.ecen and emp_in.ecen != scoped_center:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You cannot transfer employees out of the '{scoped_center}' center."
            )
        # Field authorization: Manager cannot alter salary
        if emp_in.esal is not None and emp_in.esal != emp.esal and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Administrators can adjust employee compensation."
            )

    changes_old = []
    changes_new = []

    update_data = emp_in.dict(exclude_unset=True)
    for field, new_val in update_data.items():
        old_val = getattr(emp, field)
        if old_val != new_val:
            changes_old.append(f"{field}: {old_val}")
            changes_new.append(f"{field}: {new_val}")
            setattr(emp, field, new_val)

    # If system_role or position changed, sync linked user role
    user_record = db.query(User).filter(User.employee_id == eid).first()
    if user_record and current_user.role == "ADMIN":
        if emp_in.system_role:
            user_record.role = emp_in.system_role.upper()
        elif emp_in.epos:
            if "manager" in emp_in.epos.lower():
                user_record.role = "MANAGER"
        db.commit()

    if changes_new:
        record_audit(
            db=db,
            action="EMPLOYEE_UPDATED",
            target_entity=f"Employee #{eid}",
            user_id=current_user.id,
            username=f"#{current_user.employee_id}",
            role=current_user.role,
            old_value=", ".join(changes_old),
            new_value=", ".join(changes_new),
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=req_id
        )
        cache.invalidate_prefix("analytics")

    return emp.to_dict()


@router.delete("/{eid}")
def delete_employee(
    eid: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"]))
):
    """
    Soft-delete / deactivate employee record (Admin only).
    Preserves all historical payroll and leave records while revoking user access.
    """
    req_id = get_request_id(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("User-Agent", "Unknown")

    emp = db.query(Employee).filter(Employee.eid == eid).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {eid} not found"
        )

    # Soft-delete: Mark as TERMINATED
    old_status = emp.status
    emp.status = "TERMINATED"

    # Deactivate linked user account
    linked_user = db.query(User).filter(User.employee_id == eid).first()
    if linked_user:
        linked_user.is_active = False

    db.commit()

    record_audit(
        db=db,
        action="EMPLOYEE_DEACTIVATED_TERMINATED",
        target_entity=f"Employee #{eid} ({emp.ename})",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        old_value=f"Status: {old_status}",
        new_value="Status: TERMINATED, User Account: Deactivated",
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=req_id
    )

    cache.invalidate_prefix("analytics")
    return {
        "message": f"Employee #{eid} has been deactivated (status set to TERMINATED). Historical records preserved.",
        "status": "TERMINATED"
    }
