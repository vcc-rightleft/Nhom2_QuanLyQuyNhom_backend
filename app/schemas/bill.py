from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


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
    status: str = "ACTIVE"

    class Config:
        orm_mode = True
        from_attributes = True


# === Schemas mở rộng cho Task T3CDE9A (Danh sách, Chi tiết, Sửa, Huỷ hoá đơn) ===


class BillItemInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Tên món")
    unit_price: int = Field(..., ge=0, description="Đơn giá (VND)")
    quantity: int = Field(1, ge=1, description="Số lượng")
    consumer_user_ids: List[int] = Field(
        default_factory=list,
        description="Danh sách user_id dùng chung món này",
    )


class BillShareInput(BaseModel):
    member_id: int = Field(..., gt=0, description="ID thành viên")
    amount: int = Field(..., ge=0, description="Phần tiền thành viên phải chịu (VND)")


class BillUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    bill_date: Optional[datetime] = None
    total_amount: Optional[int] = Field(None, gt=0)
    paid_by: Optional[int] = Field(None, gt=0)
    split_type: Optional[str] = Field(
        None,
        description="Kiểu chia tiền: EQUAL, ITEMIZED hoặc CUSTOM",
    )
    note: Optional[str] = None
    image_url: Optional[str] = None
    items: Optional[List[BillItemInput]] = Field(
        None,
        description="Danh sách món mới (nếu cập nhật chi tiết từng món)",
    )
    shares: Optional[List[BillShareInput]] = Field(
        None,
        description="Danh sách phần chia mới của từng thành viên",
    )
    participant_ids: Optional[List[int]] = Field(
        None,
        description="Danh sách thành viên tham gia chia đều (dùng khi split_type=EQUAL và không truyền shares)",
    )


class BillItemDetail(BaseModel):
    id: int
    bill_id: int
    name: str
    unit_price: int
    quantity: int
    line_total: int
    consumer_user_ids: List[int]


class BillShareDetail(BaseModel):
    id: int
    bill_id: int
    member_id: int
    member_name: Optional[str] = None
    amount: int
    debt_id: Optional[int] = None
    debt_status: Optional[str] = None
    paid_amount: int = 0


class BillListItem(BaseModel):
    id: int
    group_id: int
    title: str
    bill_date: datetime
    total_amount: int
    paid_by: int
    paid_by_name: Optional[str] = None
    split_type: str
    status: str
    note: Optional[str] = None
    image_url: Optional[str] = None
    item_count: int
    share_count: int
    can_edit_or_cancel: bool


class BillListResponse(BaseModel):
    group_id: int
    total: int
    page: int
    page_size: int
    items: List[BillListItem]


class BillDetailResponse(BaseModel):
    id: int
    group_id: int
    title: str
    bill_date: datetime
    total_amount: int
    paid_by: int
    paid_by_name: Optional[str] = None
    split_type: str
    status: str
    note: Optional[str] = None
    image_url: Optional[str] = None
    can_edit_or_cancel: bool
    items: List[BillItemDetail]
    shares: List[BillShareDetail]


class BillCancelResponse(BaseModel):
    message: str
    bill_id: int
    status: str
    cancelled_debts_count: int