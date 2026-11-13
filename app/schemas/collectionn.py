from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
  group_id: int
  name: str = Field(..., description="Tên đợt thu, ví dụ: Quỹ tháng 11")
  amount_per_member: float = Field(
      ..., gt=0, description="Số tiền mỗi người phải đóng (X đồng)"
  )
  created_by: int = Field(..., description="ID của Host tạo đợt thu")


class CollectionResponse(BaseModel):
  collection_id: int
  group_id: int
  name: str
  amount_per_member: float
  status: str
  created_by: int
  created_at: datetime

  class Config:
    from_attributes = True


class RecordPaymentRequest(BaseModel):
  collection_id: int
  user_id: int = Field(..., description="ID thành viên nộp quỹ")
  amount: float = Field(
      ..., gt=0, description="Số tiền nộp quỹ (bắt buộc > 0)"
  )
  description: Optional[str] = Field(None, description="Ghi chú thêm")