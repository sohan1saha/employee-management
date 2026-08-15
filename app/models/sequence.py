"""
==============================================================================
StaffSync 360 - Atomic Employee ID Sequence Model
==============================================================================
Provides atomic, lock-based continuous sequence counters per center & year partition,
guaranteeing zero duplicate ID collisions under high concurrent request volume.
"""

from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class EmployeeSequence(Base):
    """Sequence partition tracking table for atomic ID generation."""
    __tablename__ = "employee_sequences"

    prefix = Column(String(10), primary_key=True)  # e.g., "1026", "2026", "9924"
    last_sequence = Column(Integer, nullable=False, default=100)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "prefix": self.prefix,
            "last_sequence": self.last_sequence,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None
        }
