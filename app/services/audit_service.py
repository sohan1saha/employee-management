"""
==============================================================================
StaffSync 360 - Append-Only Audit Logging Service
==============================================================================
Enforces append-only system auditing. Records cannot be updated or deleted.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def record_audit(
    db: Session,
    action: str,
    target_entity: str,
    user_id: Optional[int] = None,
    username: str = "SYSTEM",
    role: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    client_ip: str = "127.0.0.1",
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None
) -> AuditLog:
    """Record an append-only audit log entry."""
    audit = AuditLog(
        user_id=user_id,
        username=username,
        role=role,
        action=action,
        target_entity=target_entity,
        old_value=old_value,
        new_value=new_value,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
