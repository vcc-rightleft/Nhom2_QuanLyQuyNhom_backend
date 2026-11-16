from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BillEqualSplitCreate(BaseModel):
    group_id: int
    title: str
    bill_date: datetime = Field(default_factory=datetime.now)
    total_amount: int = Field(..., gt=0)
    paid_by: int
    participant_ids: List[int] = Field(..., min_length=1)
    note: Optional[str] = None
    image_url: Optional[str] = None


class BillShareOut(BaseModel):
    user_id: int
    amount: float


class BillEqualSplitResponse(BaseModel):
    id: int
    group_id: int
    title: str
    bill_date: datetime
    total_amount: float
    paid_by: int
    split_type: str
    note: Optional[str] = None
    image_url: Optional[str] = None
    shares: List[BillShareOut] = []