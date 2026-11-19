from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.Calculate import get_group_fund_balance
from app.models.Collection import CollectionCampaign, MemberDebt
from app.models.FundTransaction import FundTransaction
from app.models.fund_group import FundGroup
from app.models.group_member import GroupMember
from app.models.user import User

router = APIRouter(prefix="/groups/{group_id}", tags=["Group Fund (Quỹ chung)"])


# --- SCHEMAS ---
class FundTransactionCreate(BaseModel):
    type: str = Field(..., description="INCOME hoặc EXPENSE")
    amount: int = Field(..., gt=0, description="Số tiền (VND), bắt buộc > 0")
    category: Optional[str] = None
    payer_id: Optional[int] = None
    description: Optional[str] = None
    occurred_at: Optional[datetime] = None
    proof_image_url: Optional[str] = None
    created_by: Optional[int] = 1


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1)
    amount_per_member: int = Field(..., gt=0)
    due_date: Optional[datetime] = None
    created_by: Optional[int] = 1


class ConfirmPaymentRequest(BaseModel):
    user_id: int
    amount: Optional[int] = None
    description: Optional[str] = None
    confirmed_by: Optional[int] = 1


# --- HELPERS ---
def _ensure_host(role_header: Optional[str]):
    if (role_header or "HOST").upper() != "HOST":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Host mới có quyền thực hiện thao tác này!",
        )


def _get_group_members_info(db: Session, group_id: int) -> List[dict]:
    memberships = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.status == "ACTIVE")
        .all()
    )

    if memberships:
        user_ids = [m.user_id for m in memberships]
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: u.full_name for u in users}
        return [
            {
                "user_id": m.user_id,
                "display_name": user_map.get(m.user_id, f"Thành viên #{m.user_id}"),
                "role": m.role,
            }
            for m in memberships
        ]

    users = db.query(User).limit(10).all()
    if users:
        return [
            {
                "user_id": u.id,
                "display_name": u.full_name,
                "role": "HOST" if idx == 0 else "MEMBER",
            }
            for idx, u in enumerate(users)
        ]

    return [
        {"user_id": 1, "display_name": "Lê Nguyễn Hữu Quốc", "role": "HOST"},
        {"user_id": 2, "display_name": "Nguyễn Hữu Minh Dương", "role": "MEMBER"},
        {"user_id": 3, "display_name": "Trần Thị Bảo Ngọc", "role": "MEMBER"},
        {"user_id": 4, "display_name": "Phạm Minh Tuấn", "role": "MEMBER"},
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
        "occurred_at": tx.occurred_at.isoformat() if tx.occurred_at else None,
        "proof_image_url": tx.proof_image_url,
        "created_by": tx.created_by,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }


def _serialize_collection(col: CollectionCampaign) -> dict:
    return {
        "collection_id": col.collection_id,
        "group_id": col.group_id,
        "name": col.name,
        "amount_per_member": int(col.amount_per_member),
        "due_date": col.due_date.isoformat() if col.due_date else None,
        "status": col.status,
        "created_by": col.created_by,
        "created_at": col.created_at.isoformat() if col.created_at else None,
        "member_statuses": [
            {
                "debt_id": d.debt_id,
                "user_id": d.user_id,
                "member_name": d.member_name,
                "amount_due": int(d.amount_due),
                "amount_paid": int(d.amount_paid or 0),
                "status": d.status,
                "paid_at": d.paid_at.isoformat() if d.paid_at else None,
            }
            for d in col.debts
        ],
    }


# --- ENDPOINTS ---
@router.get("/fund-overview")
def get_fund_overview(group_id: int, db: Session = Depends(get_db)):
    group = db.query(FundGroup).filter(FundGroup.id == group_id).first()
    group_info = {
        "group_id": group.id if group else group_id,
        "name": group.name if group else f"Nhóm quỹ #{group_id}",
        "description": group.description if group else "",
    }

    members = _get_group_members_info(db, group_id)
    balance = get_group_fund_balance(db, group_id)

    txs = (
        db.query(FundTransaction)
        .filter(FundTransaction.group_id == group_id)
        .order_by(FundTransaction.occurred_at.desc(), FundTransaction.transaction_id.desc())
        .all()
    )

    cols = (
        db.query(CollectionCampaign)
        .filter(CollectionCampaign.group_id == group_id)
        .order_by(CollectionCampaign.collection_id.desc())
        .all()
    )

    return {
        "group": group_info,
        "members": members,
        "balance": balance,
        "transactions": [_serialize_transaction(t) for t in txs],
        "collections": [_serialize_collection(c) for c in cols],
    }


@router.get("/fund-balance")
def get_balance(group_id: int, db: Session = Depends(get_db)):
    return get_group_fund_balance(db, group_id)


@router.get("/fund-transactions")
def list_transactions(
    group_id: int,
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(FundTransaction).filter(FundTransaction.group_id == group_id)
    if type in ("INCOME", "EXPENSE"):
        query = query.filter(FundTransaction.type == type)
    txs = query.order_by(FundTransaction.occurred_at.desc()).all()
    return [_serialize_transaction(t) for t in txs]


@router.post("/fund-transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(
    group_id: int,
    payload: FundTransactionCreate,
    x_user_role: Optional[str] = Header("HOST", alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    _ensure_host(x_user_role)

    tx_type = payload.type.upper()
    if tx_type not in ("INCOME", "EXPENSE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loại giao dịch phải là INCOME hoặc EXPENSE.",
        )

    if tx_type == "EXPENSE":
        current = get_group_fund_balance(db, group_id)
        if payload.amount > current["balance"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số dư quỹ không đủ để chi! Số dư hiện tại: {current['balance']:,} ₫.",
            )

    new_tx = FundTransaction(
        group_id=group_id,
        type=tx_type,
        amount=payload.amount,
        category=(payload.category or "").strip() or None,
        payer_id=payload.payer_id,
        description=(payload.description or "").strip() or None,
        occurred_at=payload.occurred_at or datetime.utcnow(),
        proof_image_url=(payload.proof_image_url or "").strip() or None,
        created_by=payload.created_by or 1,
        created_at=datetime.utcnow(),
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)

    return {
        "message": "Ghi nhận giao dịch thành công!",
        "transaction": _serialize_transaction(new_tx),
        "balance": get_group_fund_balance(db, group_id),
    }


@router.get("/collections")
def list_collections(group_id: int, db: Session = Depends(get_db)):
    cols = (
        db.query(CollectionCampaign)
        .filter(CollectionCampaign.group_id == group_id)
        .order_by(CollectionCampaign.collection_id.desc())
        .all()
    )
    return [_serialize_collection(c) for c in cols]


@router.post("/collections", status_code=status.HTTP_201_CREATED)
def create_collection(
    group_id: int,
    payload: CollectionCreate,
    x_user_role: Optional[str] = Header("HOST", alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    _ensure_host(x_user_role)

    new_col = CollectionCampaign(
        group_id=group_id,
        name=payload.name.strip(),
        amount_per_member=payload.amount_per_member,
        due_date=payload.due_date,
        status="ACTIVE",
        created_by=payload.created_by or 1,
        created_at=datetime.utcnow(),
    )
    db.add(new_col)
    db.flush()

    members = _get_group_members_info(db, group_id)
    for m in members:
        db.add(
            MemberDebt(
                collection_id=new_col.collection_id,
                user_id=m["user_id"],
                member_name=m["display_name"],
                amount_due=payload.amount_per_member,
                amount_paid=0,
                status="UNPAID",
            )
        )

    db.commit()
    db.refresh(new_col)
    return _serialize_collection(new_col)


@router.post("/collections/{collection_id}/confirm-payment")
def confirm_member_payment(
    group_id: int,
    collection_id: int,
    payload: ConfirmPaymentRequest,
    x_user_role: Optional[str] = Header("HOST", alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    _ensure_host(x_user_role)

    col = (
        db.query(CollectionCampaign)
        .filter(
            CollectionCampaign.collection_id == collection_id,
            CollectionCampaign.group_id == group_id,
        )
        .first()
    )
    if not col:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt thu.")

    debt = (
        db.query(MemberDebt)
        .filter(
            MemberDebt.collection_id == collection_id,
            MemberDebt.user_id == payload.user_id,
        )
        .first()
    )
    if not debt:
        raise HTTPException(status_code=404, detail="Không tìm thấy thành viên trong đợt thu.")

    remaining = max(0, int(debt.amount_due) - int(debt.amount_paid or 0))
    pay_amount = int(payload.amount) if payload.amount is not None else remaining
    if pay_amount <= 0:
        raise HTTPException(status_code=400, detail="Thành viên này đã đóng đủ hoặc số tiền <= 0.")

    now = datetime.utcnow()
    debt.amount_paid = int(debt.amount_paid or 0) + pay_amount
    debt.status = "PAID" if debt.amount_paid >= debt.amount_due else "PARTIAL"
    debt.paid_at = now

    new_tx = FundTransaction(
        group_id=group_id,
        type="INCOME",
        amount=pay_amount,
        category="Đóng quỹ định kỳ",
        payer_id=payload.user_id,
        description=payload.description or f"Xác nhận đóng đợt thu: {col.name}",
        occurred_at=now,
        created_by=payload.confirmed_by or 1,
        created_at=now,
    )
    db.add(new_tx)
    db.flush()

    if all(d.status == "PAID" for d in col.debts):
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


@router.patch("/collections/{collection_id}/cancel")
def cancel_collection(
    group_id: int,
    collection_id: int,
    x_user_role: Optional[str] = Header("HOST", alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    _ensure_host(x_user_role)

    col = (
        db.query(CollectionCampaign)
        .filter(
            CollectionCampaign.collection_id == collection_id,
            CollectionCampaign.group_id == group_id,
        )
        .first()
    )
    if not col:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt thu.")

    col.status = "CANCELLED"
    db.commit()
    db.refresh(col)
    return _serialize_collection(col)