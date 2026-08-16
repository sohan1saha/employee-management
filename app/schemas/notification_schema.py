"""Pydantic schemas for In-App Notifications."""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    category: str
    action_url: Optional[str] = None
    is_read: bool
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationFeedResponse(BaseModel):
    unread_count: int
    notifications: List[NotificationResponse]
