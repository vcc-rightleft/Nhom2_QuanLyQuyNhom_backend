from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.debt_payment import SourceTypeEnum, DebtStatusEnum, PaymentStatusEnum

class PaymentBase(BaseModel):
    amount: Decimal
    payment_method: str
    proof_image: Optional[str] = None

class PaymentCreate(PaymentBase):
    debt_id: int

class PaymentResponse(PaymentBase):
    id: int
    debt_id: int
    status: PaymentStatusEnum
    confirmed_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DebtBase(BaseModel):
    group_id: int
    source_type: SourceTypeEnum
    debtor_id: int
    payee_id: int
    amount: Decimal

class DebtCreate(DebtBase):
    pass

class DebtResponse(DebtBase):
    id: int
    paid_amount: Decimal
    status: DebtStatusEnum
    created_at: datetime
    updated_at: datetime
    payments: List[PaymentResponse] = []

    class Config:
        from_attributes = True