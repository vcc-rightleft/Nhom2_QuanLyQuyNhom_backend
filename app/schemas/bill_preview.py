from pydantic import BaseModel
from typing import List


class ItemPreview(BaseModel):
    name: str
    unit_price: int
    quantity: int
    consumers: List[int]


class CustomShare(BaseModel):
    member_id: int
    amount: int


class BillPreviewRequest(BaseModel):
    split_type: str
    total_amount: int
    participants: List[int]
    paid_by: int
    items: List[ItemPreview] = []
    shares: List[CustomShare] = []


class ShareResponse(BaseModel):
    member_id: int
    amount: int


class BillPreviewResponse(BaseModel):
    total_amount: int
    shares: List[ShareResponse]