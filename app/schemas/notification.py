from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationBase(BaseModel):
    title: str
    message: str


class NotificationCreate(NotificationBase):
    user_id: int
    target_path: Optional[str] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    target_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True