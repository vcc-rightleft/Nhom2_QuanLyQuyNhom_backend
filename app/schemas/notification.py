from typing import Optional

from pydantic import BaseModel


class NotificationBase(BaseModel):
    receiver_id: int
    type: str
    title: str
    content: str
    link: Optional[str] = None
    is_read: bool = False


class NotificationCreate(NotificationBase):
    pass


class NotificationResponse(NotificationBase):
    id: int

    class Config:
        from_attributes = True