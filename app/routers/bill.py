
from datetime import datetime
from typing import Literal, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.schemas.bill import (
    BillEqualSplitCreate,
    BillEqualSplitResponse
)
from app.crud.bill import create_equal_split_bill
from app.crud.debt import create_debts
from app.core.deps import get_current_user, ensure_group_active

from app.models.user import User
from app.models.group_member import GroupMember
from app.models.Bill import Bill
from app.models.Bill_item import BillItem
from app.models.Bill_share import BillShare
from app.models.notification import Notification


router = APIRouter(
    prefix="/bills",
    tags=["Bills"]
)


# ==========================================================
# API CHIA ĐỀU
# ==========================================================

@router.post(
    "/equal-split",
    response_model=BillEqualSplitResponse,
    status_code=status.HTTP_201_CREATED
)
def create_bill_equal_split_api(
    bill_in: BillEqualSplitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ensure_group_active(db, bill_in.group_id)

    active_members = db.query(GroupMember).filter(
        GroupMember.group_id == bill_in.group_id,
        GroupMember.status == "ACTIVE"
    ).all()

    if current_user.role.value != "ADMIN" and not any(
        m.user_id == current_user.id and m.role == "HOST"
        for m in active_members
    ):
        raise HTTPException(
            status_code=403,
            detail="Chỉ HOST của nhóm được tạo hóa đơn"
        )

    active_ids = {
        m.user_id for m in active_members
    }

    if (
        bill_in.paid_by not in active_ids
        or not set(bill_in.participant_ids).issubset(active_ids)
    ):
        raise HTTPException(
            status_code=400,
            detail="Người trả và người tham gia phải thuộc nhóm"
        )

    try:
        return create_equal_split_bill(
            db=db,
            bill_in=bill_in
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==========================================================
# SCHEMA TẠO HÓA ĐƠN
# ==========================================================

class SplitItemCreate(BaseModel):

    name: str = Field(
        min_length=1,
        max_length=255
    )

    quantity: int = Field(gt=0)

    unit_price: int = Field(gt=0)

    consumer_user_ids: List[int] = Field(
        min_length=1
    )


class SplitShareCreate(BaseModel):

    member_id: int = Field(gt=0)

    amount: int = Field(ge=0)


class BillSplitCreate(BaseModel):

    group_id: int = Field(gt=0)

    title: str = Field(
        min_length=1,
        max_length=255
    )

    paid_by: int = Field(gt=0)

    split_type: Literal[
        "EQUAL",
        "ITEMIZED",
        "CUSTOM"
    ]

    total_amount: int = Field(gt=0)

    service_fee: int = Field(
        default=0,
        ge=0
    )

    discount: int = Field(
        default=0,
        ge=0
    )

    bill_date: Optional[datetime] = None

    participant_ids: List[int] = Field(
        default_factory=list
    )

    items: List[SplitItemCreate] = Field(
        default_factory=list
    )

    shares: List[SplitShareCreate] = Field(
        default_factory=list
    )


# ==========================================================
# CHIA CHÍNH XÁC ĐẾN TỪNG ĐỒNG
# DÙNG CHO CHIA THEO MÓN, PHỤ PHÍ VÀ GIẢM GIÁ
# ==========================================================

def _distribute_vnd(
    amount: int,
    user_ids: list[int]
) -> dict[int, int]:

    ids = list(dict.fromkeys(user_ids))

    if not ids:
        raise HTTPException(
            400,
            "Chưa chọn thành viên chia hóa đơn"
        )

    base, extra = divmod(amount, len(ids))

    return {
        uid: base + (1 if idx < extra else 0)
        for idx, uid in enumerate(ids)
    }


# ==========================================================
# CHIA ĐỀU LÀM TRÒN XUỐNG ĐẾN 1.000 VND
# PHẦN CHÊNH LỆCH DO NGƯỜI ỨNG TIỀN CHỊU
# ==========================================================

def _distribute_equal_rounded(
    amount: int,
    user_ids: list[int],
    payer_id: int
) -> dict[int, int]:

    ids = list(dict.fromkeys(user_ids))

    if amount <= 0:
        raise HTTPException(
            400,
            "Tổng hóa đơn phải lớn hơn 0"
        )

    if not ids:
        raise HTTPException(
            400,
            "Chưa chọn thành viên chia hóa đơn"
        )

    if payer_id not in ids:
        raise HTTPException(
            400,
            "Người ứng tiền phải nằm trong danh sách chia đều"
        )

    number_of_members = len(ids)

    # Tính phần chia cơ bản
    # Làm tròn xuống đến 1.000 đồng
    base_share = (
        amount // number_of_members // 1000
    ) * 1000

    # Gán phần chia cơ bản cho tất cả thành viên
    allocations = {
        uid: base_share
        for uid in ids
    }

    # Tính phần còn lại sau khi làm tròn
    remainder = amount - (
        base_share * number_of_members
    )

    # Dồn phần còn lại cho người ứng tiền
    allocations[payer_id] += remainder

    # Đảm bảo tổng phân bổ bằng tổng hóa đơn
    if sum(allocations.values()) != amount:
        raise HTTPException(
            400,
            "Tổng phần chia không khớp hóa đơn"
        )

    return allocations


# ==========================================================
# API TẠO HÓA ĐƠN - HỖ TRỢ BA PHƯƠNG THỨC CHIA
# ==========================================================

@router.post(
    "/create-split",
    status_code=201
)
def create_split_bill_api(
    payload: BillSplitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # ======================================================
    # 1. KIỂM TRA THÀNH VIÊN VÀ PHÂN QUYỀN
    # ======================================================

    ensure_group_active(db, payload.group_id)

    members = db.query(GroupMember).filter(
        GroupMember.group_id == payload.group_id,
        GroupMember.status == "ACTIVE"
    ).all()

    active_ids = {
        m.user_id for m in members
    }

    if current_user.role.value != "ADMIN" and not any(
        m.user_id == current_user.id and m.role == "HOST"
        for m in members
    ):
        raise HTTPException(
            403,
            "Chỉ Host của nhóm được tạo hóa đơn"
        )

    if (
        payload.paid_by != current_user.id
        and current_user.role.value != "ADMIN"
    ):
        raise HTTPException(
            403,
            "Không được mạo danh người ứng tiền"
        )

    if payload.paid_by not in active_ids:
        raise HTTPException(
            400,
            "Người ứng tiền không thuộc nhóm"
        )

    allocations: dict[int, int] = {}


    # ======================================================
    # 2. CHIA ĐỀU - EQUAL
    # ======================================================

    if payload.split_type == "EQUAL":

        if (
            not payload.participant_ids
            or len(payload.participant_ids)
            != len(set(payload.participant_ids))
        ):
            raise HTTPException(
                400,
                "Danh sách người chia đều trống hoặc bị trùng"
            )

        if not set(
            payload.participant_ids
        ).issubset(active_ids):

            raise HTTPException(
                400,
                "Có người chia tiền không thuộc nhóm"
            )

        allocations = _distribute_equal_rounded(
            amount=payload.total_amount,
            user_ids=payload.participant_ids,
            payer_id=payload.paid_by
        )


    # ======================================================
    # 3. CHIA TÙY CHỈNH - CUSTOM
    # ======================================================

    elif payload.split_type == "CUSTOM":

        if (
            not payload.shares
            or len({
                s.member_id for s in payload.shares
            }) != len(payload.shares)
        ):
            raise HTTPException(
                400,
                "Phần chia tùy chỉnh bị trống hoặc trùng thành viên"
            )

        if not {
            s.member_id for s in payload.shares
        }.issubset(active_ids):

            raise HTTPException(
                400,
                "Có người chia tiền không thuộc nhóm"
            )

        allocations = {
            s.member_id: s.amount
            for s in payload.shares
        }

        if sum(
            allocations.values()
        ) != payload.total_amount:

            raise HTTPException(
                400,
                "Tổng chia tùy chỉnh không bằng tổng hóa đơn"
            )


    # ======================================================
    # 4. CHIA THEO MÓN - ITEMIZED
    # ======================================================

    else:

        if not payload.items:

            raise HTTPException(
                400,
                "Hóa đơn theo món cần ít nhất một món"
            )

        subtotal = 0

        for item in payload.items:

            ids = list(
                dict.fromkeys(item.consumer_user_ids)
            )

            if (
                not set(ids).issubset(active_ids)
                or len(ids) != len(item.consumer_user_ids)
            ):
                raise HTTPException(
                    400,
                    "Danh sách người dùng món không hợp lệ"
                )

            line = item.quantity * item.unit_price

            subtotal += line

            for uid, part in _distribute_vnd(
                line,
                ids
            ).items():

                allocations[uid] = (
                    allocations.get(uid, 0) + part
                )

        if (
            subtotal
            + payload.service_fee
            - payload.discount
            != payload.total_amount
        ):
            raise HTTPException(
                400,
                "Tổng tiền món và phí/giảm giá không khớp"
            )

        users = list(allocations)

        # Phân bổ phụ phí
        for uid, part in _distribute_vnd(
            payload.service_fee,
            users
        ).items():

            allocations[uid] += part

        # Phân bổ giảm giá
        for uid, part in _distribute_vnd(
            payload.discount,
            users
        ).items():

            allocations[uid] -= part

        if any(v < 0 for v in allocations.values()):

            raise HTTPException(
                400,
                "Giảm giá lớn hơn phần tiền của một thành viên; "
                "hãy điều chỉnh hóa đơn"
            )


    # ======================================================
    # 5. KIỂM TRA TỔNG PHÂN BỔ
    # ======================================================

    if (
        sum(allocations.values()) != payload.total_amount
        or any(v < 0 for v in allocations.values())
    ):
        raise HTTPException(
            400,
            "Tổng phần chia không khớp hóa đơn"
        )


    # ======================================================
    # 6. LƯU HÓA ĐƠN VÀO MYSQL
    # ======================================================

    try:

        new_bill = Bill(

            group_id=payload.group_id,

            title=payload.title.strip(),

            bill_date=(
                payload.bill_date or datetime.utcnow()
            ),

            total_amount=payload.total_amount,

            paid_by=payload.paid_by,

            payer_id=payload.paid_by,

            split_type=payload.split_type,

            items_subtotal=(
                payload.total_amount
                - payload.service_fee
                + payload.discount
            ),

            service_ship_fee=payload.service_fee,

            created_by=current_user.id,

            note=(
                f"Giảm giá: {payload.discount} VND"
                if payload.discount else None
            )
        )

        db.add(new_bill)

        db.flush()


        # ==================================================
        # 7. LƯU CHI TIẾT TỪNG MÓN
        # ==================================================

        if payload.split_type == "ITEMIZED":

            for item in payload.items:

                db.add(
                    BillItem(
                        bill_id=new_bill.id,

                        name=item.name.strip(),

                        quantity=item.quantity,

                        unit_price=item.unit_price,

                        consumer_user_ids=",".join(
                            map(
                                str,
                                item.consumer_user_ids
                            )
                        )
                    )
                )


        # ==================================================
        # 8. TẠO CÔNG NỢ VÀ THÔNG BÁO
        # ==================================================

        for member_id, amount in allocations.items():

            debt_id = None

            # Không tạo khoản nợ cho chính người ứng tiền
            if (
                member_id != payload.paid_by
                and amount > 0
            ):

                debt = create_debts(

                    db=db,

                    group_id=payload.group_id,

                    source_type="INVOICE",

                    debtor_id=member_id,

                    payee_id=payload.paid_by,

                    amount=amount,

                    source_id=new_bill.id,

                    commit=False
                )

                debt_id = debt.id

                db.add(
                    Notification(

                        user_id=member_id,

                        title=(
                            "Hóa đơn mới: " + payload.title
                        ),

                        message=(
                            f"Bạn cần thanh toán {amount:,}đ "
                            f"cho hóa đơn {payload.title}."
                        )
                    )
                )

            # Lưu phần tiền của từng thành viên
            db.add(
                BillShare(

                    bill_id=new_bill.id,

                    member_id=member_id,

                    amount=amount,

                    debt_id=debt_id
                )
            )


        # ==================================================
        # 9. COMMIT TRANSACTION
        # ==================================================

        db.commit()

        return {

            "id": new_bill.id,

            "group_id": payload.group_id,

            "split_type": payload.split_type,

            "total_amount": payload.total_amount,

            "created_debts": sum(
                1
                for uid, amt in allocations.items()
                if uid != payload.paid_by and amt > 0
            )
        }

    except Exception:

        db.rollback()

        raise
