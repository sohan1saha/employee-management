from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def record_audit(
    db: Session,
    action: str,
    target_entity: str,
    user_id: Optional[int] = None,
    username: str = "SYSTEM",
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    client_ip: str = "127.0.0.1"
) -> AuditLog:
    """Record an immutable audit log entry."""
    audit = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        target_entity=target_entity,
        old_value=old_value,
        new_value=new_value,
        client_ip=client_ip
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
