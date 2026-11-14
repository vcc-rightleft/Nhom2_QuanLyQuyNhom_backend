from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class MemberAssignItem(BaseModel):
    user_id: int
    member_name: str
    role: Optional[str] = "MEMBER"


class CollectionCreate(BaseModel):
    group_id: int = Field(1, description="ID của nhóm quỹ")
    name: str = Field(..., min_length=1, description="Tên đợt thu, ví dụ: Quỹ tháng 11")
    amount_per_member: float = Field(
        ..., gt=0, description="Số tiền mỗi người phải đóng (X đồng)"
    )
    due_date: Optional[str] = Field(None, description="Hạn đóng (YYYY-MM-DD)")
    created_by: int = Field(..., description="ID của Host tạo đợt thu")
    role: str = Field("HOST", description="Vai trò người thực hiện (chỉ HOST được phép)")
    members: Optional[List[MemberAssignItem]] = Field(
        None, description="Danh sách thành viên áp dụng trong đợt thu"
    )


class MemberDebtResponse(BaseModel):
    debt_id: int
    collection_id: int
    user_id: int
    member_name: Optional[str] = None
    role: Optional[str] = "MEMBER"
    amount_due: float
    status: str  # PAID hoặc UNPAID
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    collection_id: int
    group_id: int
    name: str
    amount_per_member: float
    due_date: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    paid_count: int = 0
    unpaid_count: int = 0
    total_members: int = 0
    total_collected: float = 0
    total_expected: float = 0
    members: List[MemberDebtResponse] = []

    class Config:
        from_attributes = True


class RecordPaymentRequest(BaseModel):
    collection_id: int = Field(..., description="ID đợt thu")
    user_id: int = Field(..., description="ID thành viên nộp quỹ")
    amount: float = Field(
        ..., gt=0, description="Số tiền nộp quỹ (bắt buộc > 0)"
    )
    created_by: int = Field(1, description="ID của Host xác nhận thu")
    role: str = Field("HOST", description="Vai trò người thực hiện (chỉ HOST được phép)")
    description: Optional[str] = Field(None, description="Ghi chú thêm")
