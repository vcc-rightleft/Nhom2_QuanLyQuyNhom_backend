from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import debt as crud_debt
from app.schemas.debt_payment import PaymentCreate, PaymentReview
from app.models.debt_payment import Debt, Payment
from app.models.group_member import GroupMember
from app.models.user import User, SystemRole
from app.core.deps import get_current_user, ensure_group_active

router = APIRouter(prefix="/debts", tags=["Debts & Funds"])

@router.get("/owed-by-me/{user_id}")
def api_owed_by_me(user_id: int, group_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.id and current_user.role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ được xem công nợ của chính mình")
    return crud_debt.get_debts_owed_by_me(db, user_id=user_id, group_id=group_id)

@router.get("/owed-to-me/{user_id}")
def api_owed_to_me(user_id: int, group_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.id and current_user.role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ được xem công nợ của chính mình")
    return crud_debt.get_debts_owed_to_me(db, user_id=user_id, group_id=group_id)

@router.post("/payments", summary="Thành viên báo cáo đã chuyển khoản nợ")
def api_create_payment_request(payment_in: PaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    debt = db.query(Debt).filter(Debt.id == payment_in.debt_id).first()
    if not debt:
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản nợ")
    ensure_group_active(db, debt.group_id)

    if debt.debtor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Chỉ người mắc nợ được báo trả nợ")
    return crud_debt.create_payment_request(db=db, obj_in=payment_in, user_id=current_user.id)

@router.put("/payments/{payment_id}/review", summary="Xác nhận hoặc từ chối thanh toán")
def api_review_payment_request(payment_id: int, review_in: PaymentReview, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán")
    debt = db.query(Debt).filter(Debt.id == payment.debt_id).first()

    if not debt:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy khoản nợ."
        )

    ensure_group_active(db, debt.group_id)
    host = bool(debt and db.query(GroupMember).filter(GroupMember.group_id == debt.group_id, GroupMember.user_id == current_user.id, GroupMember.role == "HOST", GroupMember.status == "ACTIVE").first())
    if not debt or (debt.payee_id != current_user.id and not host and current_user.role != SystemRole.ADMIN):
        raise HTTPException(status_code=403, detail="Không có quyền xác nhận khoản thanh toán này")
    return crud_debt.review_payment_request(db=db, payment_id=payment_id, review_in=review_in, reviewer_id=current_user.id)
