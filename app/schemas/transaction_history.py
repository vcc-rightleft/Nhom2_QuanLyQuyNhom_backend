from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class TransactionLogResponse(BaseModel):
    log_id: int
    transaction_id: int
    group_id: int
    action: str
    changed_by: int
    reason: str
    old_data: Optional[str] = None
    new_data: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True


class FundTransactionItemResponse(BaseModel):
    transaction_id: int
    group_id: int
    type: str
    amount: int
    category: Optional[str] = None
    payer_id: Optional[int] = None
    description: Optional[str] = None
    occurred_at: datetime
    proof_image_url: Optional[str] = None
    status: str = "ACTIVE"
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    edit_logs: List[TransactionLogResponse] = []

    class Config:
        from_attributes = True


class PaginatedTransactionHistoryResponse(BaseModel):
    group_id: int
    viewer_id: int
    page: int
    page_size: int
    total_records: int
    total_pages: int
    fund_summary: dict
    items: List[FundTransactionItemResponse]


class UpdateFundTransactionRequest(BaseModel):
    host_id: int = Field(..., description="ID của Host thực hiện sửa giao dịch")
    role: str = Field("HOST", description="Vai trò người thực hiện (bắt buộc là HOST)")
    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Lý do sửa giao dịch (bắt buộc để ghi lịch sử sửa)",
    )
    type: Optional[Literal["INCOME", "EXPENSE"]] = Field(
        None, description="Loại giao dịch mới (INCOME hoặc EXPENSE)"
    )
    amount: Optional[int] = Field(None, gt=0, description="Số tiền mới (VND, > 0)")
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="Danh mục mới")
    payer_id: Optional[int] = Field(None, description="ID người nộp/chi mới")
    description: Optional[str] = Field(None, description="Mô tả chi tiết mới")
    proof_image_url: Optional[str] = Field(None, description="URL ảnh chứng từ mới")
    occurred_at: Optional[datetime] = Field(None, description="Thời gian phát sinh giao dịch")


class CancelFundTransactionRequest(BaseModel):
    host_id: int = Field(..., description="ID của Host thực hiện huỷ giao dịch")
    role: str = Field("HOST", description="Vai trò người thực hiện (bắt buộc là HOST)")
    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Lý do huỷ giao dịch (bắt buộc để ghi lịch sử huỷ)",
    )
