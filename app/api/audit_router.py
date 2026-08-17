from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.employee import Employee
from app.models.user import User
from app.api.deps import require_roles, get_user_scope_center

router = APIRouter(prefix="/audit", tags=["Audit & Security"])


@router.get("/logs", response_model=List[dict])
def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "MANAGER"]))
):
    """
    Retrieve append-only audit trail log records (Admin and center-scoped Managers).
    Deletion and modification of audit records are blocked at ORM and API levels.
    """
    query = db.query(AuditLog)

    scoped_center = get_user_scope_center(db, current_user)
    if scoped_center and current_user.role != "ADMIN":
        center_emp_rows = db.query(Employee.eid, Employee.ename, Employee.email).filter(Employee.ecen == scoped_center).all()
        center_emp_ids = [e[0] for e in center_emp_rows]
        center_user_ids = [u[0] for u in db.query(User.id).filter(User.employee_id.in_(center_emp_ids)).all()] if center_emp_ids else []
        center_usernames = [f"#{eid}" for eid in center_emp_ids] + [str(eid) for eid in center_emp_ids] + [e[2] for e in center_emp_rows if e[2]]

        target_filters = [AuditLog.target_entity.ilike(f"%#{eid}%") for eid in center_emp_ids]
        
        conditions = [
            AuditLog.user_id == current_user.id,
            AuditLog.new_value.ilike(f"%{scoped_center}%"),
            AuditLog.old_value.ilike(f"%{scoped_center}%"),
        ]
        if center_user_ids:
            conditions.append(AuditLog.user_id.in_(center_user_ids))
        if center_usernames:
            conditions.append(AuditLog.username.in_(center_usernames))
        if target_filters:
            conditions.extend(target_filters)

        query = query.filter(or_(*conditions))

    if action and action != "ALL":
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.id.desc()).offset(offset).limit(page_size).all()
    return [log.to_dict() for log in logs]
