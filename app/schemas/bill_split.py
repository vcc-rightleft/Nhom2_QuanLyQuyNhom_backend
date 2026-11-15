from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class BillItemInput(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=255, description="Tên món ăn")
    quantity: int = Field(1, gt=0, description="Số lượng món")
    unit_price: Decimal = Field(..., gt=0, description="Đơn giá món ăn (> 0)")
    user_ids: List[int] = Field(
        ...,
        min_length=1,
        description="Danh sách user_id dùng món này (1 hoặc nhiều người; dùng chung chia đều trong số người đó)",
    )


class ItemizedSplitRequest(BaseModel):
    group_id: int = Field(..., description="ID nhóm quỹ")
    title: str = Field(..., min_length=1, max_length=255, description="Tên hoá đơn")
    payer_id: int = Field(..., description="ID người trả tiền hoá đơn (chủ nợ)")
    created_by: int = Field(..., description="ID người tạo hoá đơn")
    fee_split_mode: Literal["EQUAL", "PROPORTIONAL"] = Field(
        "EQUAL",
        description="Cách chia phí ship/phục vụ: EQUAL (chia đều) hoặc PROPORTIONAL (theo tỉ lệ tiền món)",
    )
    service_ship_fee: Decimal = Field(
        Decimal("0.00"), ge=0, description="Tổng phí ship và phí phục vụ (>= 0)"
    )
    total_amount: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Tổng tiền hoá đơn (nếu truyền vào sẽ kiểm tra khớp với tổng tiền món + phí ship/phục vụ)",
    )
    items: List[BillItemInput] = Field(..., min_length=1, description="Danh sách các món ăn")


class CustomMemberShareInput(BaseModel):
    user_id: int = Field(..., description="ID thành viên")
    amount: Decimal = Field(..., ge=0, description="Số tiền thành viên phải trả (>= 0)")


class CustomSplitRequest(BaseModel):
    group_id: int = Field(..., description="ID nhóm quỹ")
    title: str = Field(..., min_length=1, max_length=255, description="Tên hoá đơn")
    payer_id: int = Field(..., description="ID người trả tiền hoá đơn (chủ nợ)")
    created_by: int = Field(..., description="ID người tạo hoá đơn")
    total_amount: Decimal = Field(..., gt=0, description="Tổng tiền hoá đơn (bắt buộc > 0)")
    shares: List[CustomMemberShareInput] = Field(
        ...,
        min_length=1,
        description="Danh sách số tiền từng người (tổng phải khớp chính xác tổng hoá đơn)",
    )


class MemberShareResult(BaseModel):
    user_id: int
    items_amount: Decimal
    fee_amount: Decimal
    total_share_amount: Decimal
    debt_id: Optional[int] = None


class BillSplitResponse(BaseModel):
    message: str
    bill_id: int
    group_id: int
    title: str
    payer_id: int
    split_type: str
    fee_split_mode: Optional[str] = None
    items_subtotal: Decimal
    service_ship_fee: Decimal
    total_amount: Decimal
    total_debts_created: int
    shares: List[MemberShareResult]
