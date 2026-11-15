from typing import Optional

from pydantic import BaseModel


class BillItemBase(BaseModel):
    bill_id: int
    name: str
    unit_price: int
    quantity: int
    consumer_user_ids: Optional[str] = None


class BillItemCreate(BillItemBase):
    pass


class BillItemResponse(BillItemBase):
    id: int

    class Config:
        from_attributes = True