from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class BillBase(BaseModel):
    group_id: int
    title: str
    bill_date: datetime
    total_amount: int
    paid_by: int
    split_type: str
    note: Optional[str] = None
    image_url: Optional[str] = None


class BillCreate(BillBase):
    pass


class BillUpdate(BaseModel):
    title: Optional[str] = None
    bill_date: Optional[datetime] = None
    total_amount: Optional[int] = None
    paid_by: Optional[int] = None
    split_type: Optional[str] = None
    note: Optional[str] = None
    image_url: Optional[str] = None


class BillResponse(BillBase):
    id: int

    class Config:
        from_attributes = True