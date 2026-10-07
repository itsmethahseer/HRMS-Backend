from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.modules.notifications.models import NotificationTypeEnum


class NotificationCreate(BaseModel):
    recipient_id: int
    title: str
    message: str
    notification_type: Optional[NotificationTypeEnum] = NotificationTypeEnum.system
    link: Optional[str] = None


class NotificationOut(BaseModel):
    id: int
    recipient_id: int
    sender_id: Optional[int] = None
    title: str
    message: str
    notification_type: NotificationTypeEnum
    is_read: bool
    link: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationSummary(BaseModel):
    total: int
    unread: int
