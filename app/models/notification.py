"""User In-App Notification and Alert Model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="SYSTEM", nullable=False)  # LEAVE, PAYROLL, APPRAISAL, ATTENDANCE, SYSTEM, SECURITY
    action_url = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User", backref="notifications")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "action_url": self.action_url,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
