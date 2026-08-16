"""
==============================================================================
StaffSync 360 - Performance Reviews & Appraisals API Router
==============================================================================
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_request_id
from app.models.user import User
from app.models.employee import Employee
from app.models.performance import PerformanceReview
from app.schemas.performance_schema import (
    PerformanceReviewCreate,
    PerformanceAcknowledgeRequest,
    PerformanceReviewResponse
)
from app.services.audit_service import record_audit
from app.services.email_service import notify_performance_review

router = APIRouter(prefix="/performance", tags=["Performance & Appraisals"])


@router.post("/reviews", response_model=PerformanceReviewResponse)
def create_performance_review(
    payload: PerformanceReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or publish an official quarterly employee performance review (Manager/Admin)."""
    if current_user.role not in ["ADMIN", "MANAGER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Managers and System Administrators can author performance appraisals."
        )

    target_emp = db.query(Employee).filter(Employee.eid == payload.employee_id).first()
    if not target_emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee #{payload.employee_id} not found."
        )

    # Scoping check for regional managers
    if current_user.role == "MANAGER":
        mgr_center = current_user.employee.ecen if current_user.employee else None
        if mgr_center and mgr_center != "Corporate HQ" and target_emp.ecen != mgr_center:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: You can only conduct appraisals for employees in {mgr_center}."
            )

    review = PerformanceReview(
        employee_id=payload.employee_id,
        reviewer_id=current_user.id,
        review_period=payload.review_period,
        rating=payload.rating,
        goals_met=payload.goals_met,
        strengths=payload.strengths,
        areas_for_improvement=payload.areas_for_improvement,
        manager_feedback=payload.manager_feedback,
        status=payload.status or "FINALIZED"
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Trigger In-App & Email Notification to the Employee
    notify_performance_review(
        db=db,
        employee_id=payload.employee_id,
        review_period=payload.review_period,
        rating=payload.rating
    )

    record_audit(
        db=db,
        action="PERFORMANCE_REVIEW_PUBLISHED",
        target_entity=f"Employee #{payload.employee_id} ({target_emp.ename})",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Period: {payload.review_period} | Rating: {payload.rating:.1f}/5.0 | Goals: {payload.goals_met}",
        client_ip=request.client.host if request.client else "127.0.0.1",
        request_id=get_request_id(request)
    )

    return review.to_dict()


@router.get("/reviews", response_model=List[PerformanceReviewResponse])
def list_performance_reviews(
    center: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List performance reviews based on user role and center isolation."""
    query = db.query(PerformanceReview).join(Employee, PerformanceReview.employee_id == Employee.eid)

    if current_user.role == "EMPLOYEE":
        query = query.filter(PerformanceReview.employee_id == current_user.employee_id)
    elif current_user.role == "MANAGER":
        mgr_center = current_user.employee.ecen if current_user.employee else None
        if mgr_center and mgr_center != "Corporate HQ":
            query = query.filter(Employee.ecen == mgr_center)
        elif center and center != "ALL":
            query = query.filter(Employee.ecen == center)
    elif center and center != "ALL":
        query = query.filter(Employee.ecen == center)

    offset = (page - 1) * page_size
    reviews = query.order_by(PerformanceReview.id.desc()).offset(offset).limit(page_size).all()
    return [r.to_dict() for r in reviews]


@router.patch("/reviews/{review_id}/acknowledge", response_model=PerformanceReviewResponse)
def acknowledge_performance_review(
    review_id: int,
    payload: PerformanceAcknowledgeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Employee acknowledges their quarterly performance appraisal."""
    review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Performance review #{review_id} not found."
        )

    if review.employee_id != current_user.employee_id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only acknowledge your own performance appraisals."
        )

    review.is_acknowledged = True
    review.acknowledged_at = datetime.now(timezone.utc)
    if payload.employee_comments:
        review.employee_comments = payload.employee_comments

    db.commit()
    db.refresh(review)

    record_audit(
        db=db,
        action="PERFORMANCE_REVIEW_ACKNOWLEDGED",
        target_entity=f"Performance Review #{review_id}",
        user_id=current_user.id,
        username=f"#{current_user.employee_id}",
        role=current_user.role,
        new_value=f"Acknowledged appraisal for {review.review_period}",
        client_ip=request.client.host if request.client else "127.0.0.1",
        request_id=get_request_id(request)
    )

    return review.to_dict()
