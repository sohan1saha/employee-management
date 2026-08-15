from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee_schema import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.api.deps import get_current_user, require_roles, get_user_scope_center
from app.services.audit_service import record_audit

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=List[dict])
def list_employees(
    search: Optional[str] = Query(None, description="Search by name, ID, or position"),
    center: Optional[str] = Query(None, description="Filter by center/branch"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ON_LEAVE, TERMINATED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve list of employees. Employees see only themselves, managers only their center."""
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

    employees = query.order_by(Employee.eid.asc()).all()
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


def get_next_recommended_employee_id(db: Session, center: str, doj_str: Optional[str] = None) -> int:
    """
    Generate next recommended continuous Employee ID following pattern:
    [Center Code (2 digits)][Year of Joining (2 digits)][Sequential Main ID (3+ digits)]
    Example: Bangalore (10) + 2026 (26) + 101 => 1026101
    """
    from datetime import datetime
    year_code = "26"
    if doj_str:
        try:
            year_val = datetime.strptime(doj_str[:10], "%Y-%m-%d").year
            year_code = str(year_val)[-2:]
        except Exception:
            year_code = str(datetime.utcnow().year)[-2:]
    else:
        year_code = str(datetime.utcnow().year)[-2:]

    c_code = get_center_code(center)
    prefix = f"{c_code}{year_code}"

    # Query all existing employee IDs
    eids = [e[0] for e in db.query(Employee.eid).all()]
    matching_eids = [eid for eid in eids if str(eid).startswith(prefix) and len(str(eid)) >= 7]

    if matching_eids:
        next_eid = max(matching_eids) + 1
    else:
        next_eid = int(f"{prefix}101")

    return next_eid


@router.get("/next-id")
def get_next_employee_id(
    center: Optional[str] = Query(None, description="Center name e.g. Bangalore"),
    doj: Optional[str] = Query(None, description="Date of joining YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Calculate and return next recommended continuous employee ID following [CenterCode][YY][Seq] pattern."""
    scoped_center = get_user_scope_center(db, current_user)
    effective_center = scoped_center or center or "Bangalore"
    next_id = get_next_recommended_employee_id(db, effective_center, doj)
    return {
        "next_id": next_id,
        "center": effective_center,
        "center_code": get_center_code(effective_center),
        "pattern": f"[{get_center_code(effective_center)}][YY][Sequence]"
    }


@router.get("/centers/list")
def get_centers_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve distinct list of active centers (scoped for managers and employees)."""
    if current_user.role == "EMPLOYEE" and current_user.employee_id:
        emp = db.query(Employee).filter(Employee.eid == current_user.employee_id).first()
        return [emp.ecen] if emp and emp.ecen else []

    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center:
        return [scoped_center]
    centers = db.query(Employee.ecen).distinct().all()
    return [c[0] for c in centers if c[0]]


@router.get("/{eid}")
def get_employee(
    eid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve detailed record of a single employee."""
    emp = db.query(Employee).filter(Employee.eid == eid).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {eid} not found"
        )

    if current_user.role == "EMPLOYEE" and current_user.employee_id != eid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are only authorized to view your own employee profile."
        )

    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and emp.ecen != scoped_center:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You are only authorized to view employees in the '{scoped_center}' center."
        )
    return emp.to_dict()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_employee(
    emp_in: EmployeeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Create a new employee record (Admin or Manager)."""
    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and emp_in.ecen != scoped_center:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. As manager of '{scoped_center}', you can only add employees to your center."
        )

    # Check if ID already exists
    existing = db.query(Employee).filter(Employee.eid == emp_in.eid).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee with ID {emp_in.eid} already exists!"
        )

    email = emp_in.email or f"emp{emp_in.eid}@staffsync.internal"
    
    # Check if email exists
    existing_email = db.query(Employee).filter(Employee.email == email).first()
    if existing_email:
        email = f"emp{emp_in.eid}_{emp_in.ename.lower().replace(' ', '')}@staffsync.internal"

    employee = Employee(
        eid=emp_in.eid,
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

    # Automatic Audit Logging
    client_ip = request.client.host if request.client else "127.0.0.1"
    record_audit(
        db=db,
        action="EMPLOYEE_CREATED",
        target_entity=f"Employee #{employee.eid}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        new_value=f"Name: {employee.ename}, Center: {employee.ecen}, Pos: {employee.epos}, Sal: {employee.esal}",
        client_ip=client_ip
    )

    return employee.to_dict()


@router.put("/{eid}")
def update_employee(
    eid: int,
    emp_in: EmployeeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """Update employee details with change tracking in audit logs."""
    emp = db.query(Employee).filter(Employee.eid == eid).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {eid} not found"
        )

    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center:
        if emp.ecen != scoped_center:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You are only authorized to edit employees in the '{scoped_center}' center."
            )
        if emp_in.ecen and emp_in.ecen != scoped_center:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You cannot transfer employees out of the '{scoped_center}' center."
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

    db.commit()
    db.refresh(emp)

    # Audit log if anything changed
    if changes_new:
        client_ip = request.client.host if request.client else "127.0.0.1"
        record_audit(
            db=db,
            action="EMPLOYEE_UPDATED",
            target_entity=f"Employee #{eid}",
            user_id=current_user.id,
            username=f"#{current_user.employee_id}",
            old_value=", ".join(changes_old),
            new_value=", ".join(changes_new),
            client_ip=client_ip
        )

    return emp.to_dict()


@router.delete("/{eid}")
def delete_employee(
    eid: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"]))
):
    """Delete an employee record (Admin only)."""
    emp = db.query(Employee).filter(Employee.eid == eid).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {eid} not found"
        )

    emp_snapshot = f"Name: {emp.ename}, Center: {emp.ecen}, Pos: {emp.epos}, Sal: {emp.esal}"
    db.delete(emp)
    db.commit()

    # Record Audit Log
    client_ip = request.client.host if request.client else "127.0.0.1"
    record_audit(
        db=db,
        action="EMPLOYEE_DELETED",
        target_entity=f"Employee #{eid}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        old_value=emp_snapshot,
        client_ip=client_ip
    )

    return {"message": f"Employee record #{eid} successfully deleted"}
