"""
==============================================================================
StaffSync 360 - In-App Notifications API Router
==============================================================================
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification_schema import NotificationResponse, NotificationFeedResponse

router = APIRouter(prefix="/notifications", tags=["Notification Center"])


@router.get("", response_model=NotificationFeedResponse)
def get_user_notifications(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve active user notification feed and unread counter."""
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).count()

    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.id.desc()).limit(limit).all()

    return {
        "unread_count": unread_count,
        "notifications": [n.to_dict() for n in notifications]
    }


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found."
        )

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif.to_dict()


@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all unread notifications as read for current user."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()

    return {"message": "All notifications marked as read."}
