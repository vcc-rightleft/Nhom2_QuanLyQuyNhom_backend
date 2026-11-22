
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.Calculate import get_group_fund_balance
from app.models.Collection import CollectionCampaign, MemberDebt
from app.models.FundTransaction import FundTransaction
from app.models.fund_group import FundGroup
from app.models.group_member import GroupMember
from app.models.user import User
from app.core.deps import require_group_member, require_group_host


router = APIRouter(
    prefix="/groups/{group_id}",
    tags=["Group Fund (Quỹ chung)"]
)


# ==========================================
# SCHEMAS
# ==========================================

class FundTransactionCreate(BaseModel):
    type: str = Field(..., description="INCOME hoặc EXPENSE")
    amount: int = Field(..., gt=0, description="Số tiền VND")
    category: Optional[str] = None
    payer_id: Optional[int] = None
    description: Optional[str] = None
    occurred_at: Optional[datetime] = None
    proof_image_url: Optional[str] = None
    created_by: Optional[int] = None


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1)
    amount_per_member: int = Field(..., gt=0)
    due_date: Optional[datetime] = None
    created_by: Optional[int] = None


class ConfirmPaymentRequest(BaseModel):
    user_id: int
    amount: Optional[int] = None
    description: Optional[str] = None
    confirmed_by: Optional[int] = None


# ==========================================
# HELPERS
# ==========================================

def _get_group_members_info(
    db: Session,
    group_id: int
) -> List[dict]:

    memberships = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.status == "ACTIVE"
        )
        .all()
    )

    if not memberships:
        return []

    user_ids = [member.user_id for member in memberships]

    users = (
        db.query(User)
        .filter(User.id.in_(user_ids))
        .all()
    )

    user_map = {
        user.id: user.full_name
        for user in users
    }

    return [
        {
            "user_id": member.user_id,
            "display_name": user_map.get(
                member.user_id,
                f"Thành viên #{member.user_id}"
            ),
            "role": member.role,
        }
        for member in memberships
    ]


def _serialize_transaction(tx: FundTransaction) -> dict:
    return {
        "transaction_id": tx.transaction_id,
        "group_id": tx.group_id,
        "type": tx.type,
        "amount": int(tx.amount),
        "category": tx.category,
        "payer_id": tx.payer_id,
        "description": tx.description,
        "occurred_at": (
            tx.occurred_at.isoformat()
            if tx.occurred_at else None
        ),
        "proof_image_url": tx.proof_image_url,
        "created_by": tx.created_by,
        "status": tx.status,
        "created_at": (
            tx.created_at.isoformat()
            if tx.created_at else None
        ),
    }


def _serialize_collection(col: CollectionCampaign) -> dict:
    return {
        "collection_id": col.collection_id,
        "group_id": col.group_id,
        "name": col.name,
        "amount_per_member": int(col.amount_per_member),
        "due_date": (
            col.due_date.isoformat()
            if col.due_date else None
        ),
        "status": col.status,
        "created_by": col.created_by,
        "created_at": (
            col.created_at.isoformat()
            if col.created_at else None
        ),
        "member_statuses": [
            {
                "debt_id": debt.debt_id,
                "user_id": debt.user_id,
                "member_name": debt.member_name,
                "amount_due": int(debt.amount_due),
                "amount_paid": int(debt.amount_paid or 0),
                "status": debt.status,
                "paid_at": (
                    debt.paid_at.isoformat()
                    if debt.paid_at else None
                ),
            }
            for debt in col.debts
        ],
    }


# ==========================================
# 1. TỔNG QUAN QUỸ NHÓM
# ==========================================

@router.get("/fund-overview")
def get_fund_overview(
    group_id: int,
    current_user: User = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    group = (
        db.query(FundGroup)
        .filter(FundGroup.id == group_id)
        .first()
    )

    group_info = {
        "group_id": group.id if group else group_id,
        "name": (
            group.name if group
            else f"Nhóm quỹ #{group_id}"
        ),
        "description": (
            group.description if group else ""
        ),
    }

    members = _get_group_members_info(db, group_id)
    balance = get_group_fund_balance(db, group_id)

    transactions = (
        db.query(FundTransaction)
        .filter(FundTransaction.group_id == group_id)
        .order_by(
            FundTransaction.occurred_at.desc(),
            FundTransaction.transaction_id.desc()
        )
        .all()
    )

    collections = (
        db.query(CollectionCampaign)
        .filter(CollectionCampaign.group_id == group_id)
        .order_by(CollectionCampaign.collection_id.desc())
        .all()
    )

    return {
        "group": group_info,
        "members": members,
        "balance": balance,
        "transactions": [
            _serialize_transaction(tx)
            for tx in transactions
        ],
        "collections": [
            _serialize_collection(col)
            for col in collections
        ],
    }


# ==========================================
# 2. XEM SỐ DƯ QUỸ
# ==========================================

@router.get("/fund-balance")
def get_balance(
    group_id: int,
    current_user: User = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    return get_group_fund_balance(db, group_id)


# ==========================================
# 3. DANH SÁCH GIAO DỊCH
# ==========================================

@router.get("/fund-transactions")
def list_transactions(
    group_id: int,
    type: Optional[str] = Query(None),
    current_user: User = Depends(require_group_member),
    db: Session = Depends(get_db),
):

    query = db.query(FundTransaction).filter(
        FundTransaction.group_id == group_id
    )

    if type in ("INCOME", "EXPENSE"):
        query = query.filter(FundTransaction.type == type)

    transactions = (
        query.order_by(
            FundTransaction.occurred_at.desc()
        )
        .all()
    )

    return [
        _serialize_transaction(tx)
        for tx in transactions
    ]


# ==========================================
# 4. HOST TẠO GIAO DỊCH THU / CHI
# ==========================================

@router.post(
    "/fund-transactions",
    status_code=status.HTTP_201_CREATED
)
def create_transaction(
    group_id: int,
    payload: FundTransactionCreate,
    current_user: User = Depends(require_group_host),
    db: Session = Depends(get_db),
):

    tx_type = payload.type.upper()

    if tx_type not in ("INCOME", "EXPENSE"):
        raise HTTPException(
            status_code=400,
            detail="Loại giao dịch phải là INCOME hoặc EXPENSE."
        )

    if payload.payer_id is not None:
        member = (
            db.query(GroupMember)
            .filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == payload.payer_id,
                GroupMember.status == "ACTIVE"
            )
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=400,
                detail="Người đóng hoặc nhận tiền không thuộc nhóm."
            )

    if tx_type == "EXPENSE":
        current = get_group_fund_balance(db, group_id)

        if payload.amount > current["balance"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Số dư quỹ không đủ để chi! "
                    f"Số dư hiện tại: {current['balance']:,} ₫."
                )
            )

    now = datetime.utcnow()

    new_tx = FundTransaction(
        group_id=group_id,
        type=tx_type,
        amount=payload.amount,
        category=(
            (payload.category or "").strip() or None
        ),
        payer_id=payload.payer_id,
        description=(
            (payload.description or "").strip() or None
        ),
        occurred_at=payload.occurred_at or now,
        proof_image_url=(
            (payload.proof_image_url or "").strip() or None
        ),
        created_by=current_user.id,
        created_at=now,
    )

    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)

    return {
        "message": "Ghi nhận giao dịch thành công!",
        "transaction": _serialize_transaction(new_tx),
        "balance": get_group_fund_balance(db, group_id),
    }


# ==========================================
# 5. XEM CÁC ĐỢT THU QUỸ
# ==========================================

@router.get("/collections")
def list_collections(
    group_id: int,
    current_user: User = Depends(require_group_member),
    db: Session = Depends(get_db),
):

    collections = (
        db.query(CollectionCampaign)
        .filter(CollectionCampaign.group_id == group_id)
        .order_by(CollectionCampaign.collection_id.desc())
        .all()
    )

    return [
        _serialize_collection(col)
        for col in collections
    ]


# ==========================================
# 6. HOST TẠO ĐỢT THU QUỸ
# ==========================================

@router.post(
    "/collections",
    status_code=status.HTTP_201_CREATED
)
def create_collection(
    group_id: int,
    payload: CollectionCreate,
    current_user: User = Depends(require_group_host),
    db: Session = Depends(get_db),
):

    now = datetime.utcnow()

    new_col = CollectionCampaign(
        group_id=group_id,
        name=payload.name.strip(),
        amount_per_member=payload.amount_per_member,
        due_date=payload.due_date,
        status="ACTIVE",
        created_by=current_user.id,
        created_at=now,
    )

    db.add(new_col)
    db.flush()

    members = _get_group_members_info(db, group_id)

    for member in members:
        db.add(
            MemberDebt(
                collection_id=new_col.collection_id,
                user_id=member["user_id"],
                member_name=member["display_name"],
                amount_due=payload.amount_per_member,
                amount_paid=0,
                status="UNPAID",
            )
        )

    db.commit()
    db.refresh(new_col)

    return _serialize_collection(new_col)


# ==========================================
# 7. HOST XÁC NHẬN THÀNH VIÊN ĐÓNG QUỸ
# ==========================================

@router.post("/collections/{collection_id}/confirm-payment")
def confirm_member_payment(
    group_id: int,
    collection_id: int,
    payload: ConfirmPaymentRequest,
    current_user: User = Depends(require_group_host),
    db: Session = Depends(get_db),
):

    col = (
        db.query(CollectionCampaign)
        .filter(
            CollectionCampaign.collection_id == collection_id,
            CollectionCampaign.group_id == group_id,
        )
        .first()
    )

    if not col:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đợt thu."
        )

    if col.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Đợt thu không còn hoạt động."
        )

    debt = (
        db.query(MemberDebt)
        .filter(
            MemberDebt.collection_id == collection_id,
            MemberDebt.user_id == payload.user_id,
        )
        .first()
    )

    if not debt:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thành viên trong đợt thu."
        )

    remaining = max(
        0,
        int(debt.amount_due) - int(debt.amount_paid or 0)
    )

    pay_amount = (
        int(payload.amount)
        if payload.amount is not None
        else remaining
    )

    if pay_amount <= 0 or pay_amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=(
                "Số tiền đóng phải lớn hơn 0 "
                "và không vượt quá số tiền còn lại."
            )
        )

    now = datetime.utcnow()

    debt.amount_paid = (
        int(debt.amount_paid or 0) + pay_amount
    )

    debt.status = (
        "PAID"
        if debt.amount_paid >= debt.amount_due
        else "PARTIAL"
    )

    if debt.status == "PAID":
        debt.paid_at = now

    new_tx = FundTransaction(
        group_id=group_id,
        type="INCOME",
        amount=pay_amount,
        category="Đóng quỹ định kỳ",
        payer_id=payload.user_id,
        description=(
            payload.description
            or f"Xác nhận đóng đợt thu: {col.name}"
        ),
        occurred_at=now,
        created_by=current_user.id,
        created_at=now,
    )

    db.add(new_tx)
    db.flush()

    if all(
        member_debt.status == "PAID"
        for member_debt in col.debts
    ):
        col.status = "COMPLETED"

    db.commit()
    db.refresh(col)
    db.refresh(new_tx)

    return {
        "message": "Xác nhận đóng quỹ thành công!",
        "collection": _serialize_collection(col),
        "transaction": _serialize_transaction(new_tx),
        "balance": get_group_fund_balance(db, group_id),
    }


# ==========================================
# 8. HOST HỦY ĐỢT THU
# ==========================================

@router.patch("/collections/{collection_id}/cancel")
def cancel_collection(
    group_id: int,
    collection_id: int,
    current_user: User = Depends(require_group_host),
    db: Session = Depends(get_db),
):

    col = (
        db.query(CollectionCampaign)
        .filter(
            CollectionCampaign.collection_id == collection_id,
            CollectionCampaign.group_id == group_id,
        )
        .first()
    )

    if not col:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đợt thu."
        )

    if col.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể hủy đợt thu đang hoạt động."
        )

    col.status = "CANCELLED"

    db.commit()
    db.refresh(col)

    return _serialize_collection(col)
