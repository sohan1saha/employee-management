"""Performance Appraisal and Quarterly Review Model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.eid", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_period = Column(String(50), nullable=False)  # e.g., "Q1 2026", "Q2 2026", "Annual 2025"
    rating = Column(Float, nullable=False)  # 1.0 to 5.0
    goals_met = Column(String(30), default="MET", nullable=False)  # EXCEEDED, MET, PARTIALLY_MET, NEEDS_IMPROVEMENT
    strengths = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    manager_feedback = Column(Text, nullable=False)
    employee_comments = Column(Text, nullable=True)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="FINALIZED", nullable=False)  # DRAFT, SUBMITTED, FINALIZED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    employee = relationship("Employee", backref="performance_reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.ename if self.employee else None,
            "center": self.employee.ecen if self.employee else None,
            "position": self.employee.epos if self.employee else None,
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer.role if self.reviewer else None,
            "review_period": self.review_period,
            "rating": round(float(self.rating), 1) if self.rating is not None else 0.0,
            "goals_met": self.goals_met,
            "strengths": self.strengths,
            "areas_for_improvement": self.areas_for_improvement,
            "manager_feedback": self.manager_feedback,
            "employee_comments": self.employee_comments,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
