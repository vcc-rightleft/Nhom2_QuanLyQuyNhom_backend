from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- SCHEMAS CHO FUND TRANSACTION ---
class FundTransactionBase(BaseModel):
    type: str  # 'INCOME' hoac 'EXPENSE'
    amount: int
    category: Optional[str] = None
    payer_id: Optional[int] = None
    description: Optional[str] = None
    occurred_at: Optional[datetime] = None
    proof_image_url: Optional[str] = None

class FundTransactionCreate(FundTransactionBase):
    group_id: int

class FundTransactionResponse(FundTransactionBase):
    transaction_id: int
    group_id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schema tinh so du quy (So du = Tong THU - Tong CHI)
class FundBalanceResponse(BaseModel):
    group_id: int
    total_income: int
    total_expense: int
    balance: int


# --- SCHEMAS CHO COLLECTION (ĐỢT THU) ---
class CollectionBase(BaseModel):
    name: str
    amount_per_member: int
    due_date: Optional[datetime] = None

class CollectionCreate(CollectionBase):
    group_id: int

class CollectionResponse(CollectionBase):
    collection_id: int
    group_id: int
    status: str
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True