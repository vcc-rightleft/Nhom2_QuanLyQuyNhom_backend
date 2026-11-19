from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import debt as crud_debt
from app.schemas.debt_payment import PaymentCreate, PaymentReview, PaymentResponse

router = APIRouter(prefix="/debts", tags=["Debts & Funds"])


@router.get("/owed-by-me/{user_id}")
def api_owed_by_me(user_id: int, group_id: int = None, db: Session = Depends(get_db)):
    """Lấy danh sách các khoản tôi nợ người khác"""
    return crud_debt.get_debts_owed_by_me(db, user_id=user_id, group_id=group_id)


@router.get("/owed-to-me/{user_id}")
def api_owed_to_me(user_id: int, group_id: int = None, db: Session = Depends(get_db)):
    """Lấy danh sách người khác nợ tôi"""
    return crud_debt.get_debts_owed_to_me(db, user_id=user_id, group_id=group_id)


@router.post("/payments", summary="Thành viên báo cáo đã chuyển khoản nợ")
def api_create_payment_request(
    payment_in: PaymentCreate,
    db: Session = Depends(get_db)
):
    """
    Thành viên báo cáo đã chuyển khoản (số tiền, ảnh minh chứng, phương thức).
    Hệ thống kiểm tra không cho phép trả vượt số nợ còn lại.
    """
    return crud_debt.create_payment_request(db=db, obj_in=payment_in, user_id=1)


@router.put("/payments/{payment_id}/review", summary="Host hoặc người được trả xác nhận/từ chối thanh toán")
def api_review_payment_request(
    payment_id: int,
    review_in: PaymentReview,
    db: Session = Depends(get_db)
):
    """
    Host xác nhận (CONFIRMED) hoặc từ chối (REJECTED) thanh toán.
    Nếu CONFIRMED, tự động gạch nợ (cập nhật paid_amount và trạng thái nợ thành PARTIAL hoặc PAID).
    """
    return crud_debt.review_payment_request(db=db, payment_id=payment_id, review_in=review_in, reviewer_id=1)