from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ExpenseCreateRequest(BaseModel):
    group_id: int = Field(1, description="ID của nhóm quỹ")
    amount: int = Field(..., gt=0, description="Số tiền chi (VND, bắt buộc > 0)")
    category: str = Field(..., min_length=1, max_length=100, description="Danh mục chi (VD: Ăn uống, In ấn, Dụng cụ...)")
    proof_image_url: str = Field(..., min_length=1, max_length=500, description="Đường dẫn/URL ảnh chứng từ")
    payer_id: Optional[int] = Field(None, description="ID người trực tiếp chi tiền")
    description: Optional[str] = Field(None, description="Ghi chú chi tiết khoản chi")
    created_by: int = Field(1, description="ID của Host thực hiện ghi khoản chi")
    role: str = Field("HOST", description="Vai trò người thực hiện (chỉ HOST được phép)")


class IncomeCreateRequest(BaseModel):
    group_id: int = Field(1, description="ID của nhóm quỹ")
    amount: int = Field(..., gt=0, description="Số tiền thu (VND, bắt buộc > 0)")
    category: str = Field("Thu quỹ chung", min_length=1, max_length=100, description="Danh mục khoản thu")
    payer_id: Optional[int] = Field(None, description="ID thành viên nộp tiền")
    description: Optional[str] = Field(None, description="Ghi chú chi tiết khoản thu")
    proof_image_url: Optional[str] = Field(None, description="Ảnh minh chứng (nếu có)")
    created_by: int = Field(1, description="ID của Host thực hiện ghi khoản thu")
    role: str = Field("HOST", description="Vai trò người thực hiện (chỉ HOST được phép)")


class ExpenseTransactionResponse(BaseModel):
    transaction_id: int
    group_id: int
    type: str
    amount: int
    category: Optional[str] = None
    proof_image_url: Optional[str] = None
    payer_id: Optional[int] = None
    description: Optional[str] = None
    occurred_at: datetime
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecordExpenseResponse(BaseModel):
    message: str
    transaction: ExpenseTransactionResponse
    fund_summary: dict
