from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, event
from app.core.database import Base


class AuditLog(Base):
    """
    Append-Only Audit Log Record:
    Captures actor, action, diffs, client IP, user agent, and request correlation ID.
    Modifications and deletions are strictly blocked via SQLAlchemy ORM event listeners.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=False)
    role = Column(String(20), nullable=True)
    action = Column(String(60), nullable=False, index=True)
    target_entity = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    client_ip = Column(String(45), default="127.0.0.1", nullable=False)
    user_agent = Column(String(255), nullable=True)
    request_id = Column(String(36), index=True, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_action_timestamp", "action", "timestamp"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "action": self.action,
            "target_entity": self.target_entity,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None
        }


# =============================================================================
# ORM-Level Append-Only Immutability Enforcement
# =============================================================================

def _block_audit_update(mapper, connection, target):
    raise PermissionError("CRITICAL AUDIT INTEGRITY ERROR: AuditLog records are append-only and cannot be updated.")


def _block_audit_delete(mapper, connection, target):
    raise PermissionError("CRITICAL AUDIT INTEGRITY ERROR: AuditLog records are append-only and cannot be deleted.")


event.listen(AuditLog, "before_update", _block_audit_update)
event.listen(AuditLog, "before_delete", _block_audit_delete)
