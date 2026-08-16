"""Pydantic schemas for Performance Reviews and Quarterly Appraisals."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PerformanceReviewCreate(BaseModel):
    employee_id: int
    review_period: str = Field(..., json_schema_extra={"example": "Q1 2026"})
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    goals_met: str = Field(default="MET", description="EXCEEDED, MET, PARTIALLY_MET, NEEDS_IMPROVEMENT")
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    manager_feedback: str
    status: Optional[str] = "FINALIZED"


class PerformanceAcknowledgeRequest(BaseModel):
    employee_comments: Optional[str] = None


class PerformanceReviewResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    center: Optional[str] = None
    position: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_role: Optional[str] = None
    review_period: str
    rating: float
    goals_met: str
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    manager_feedback: str
    employee_comments: Optional[str] = None
    is_acknowledged: bool
    acknowledged_at: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
