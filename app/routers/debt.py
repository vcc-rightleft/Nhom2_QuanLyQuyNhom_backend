from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.crud import debt as crud_debt
from app.schemas.debt_payment import PaymentCreate, PaymentReview, PaymentResponse

router = APIRouter(prefix="/debts", tags=["Debts & Funds Management"])

@router.get("/owed-by-me/{user_id}", summary="Lấy danh sách các khoản tôi nợ (theo nhóm hoặc tổng các nhóm)")
def api_get_debts_owed_by_me(
    user_id: int, 
    group_id: Optional[int] = Query(None, description="Mã nhóm quỹ (bỏ trống để lấy tổng tất cả các nhóm)"), 
    db: Session = Depends(get_db)
):
    """
    API trả về danh sách các khoản nợ mà user_id đang phải trả cho người khác.
    """
    # Đổi thành get_debts_owed_by_me cho khớp với file crud/debt.py
    debts = crud_debt.get_debts_owed_by_me(db, user_id=user_id, group_id=group_id)
    
    return {
        "user_id": user_id,
        "group_id": group_id if group_id else "all_groups",
        "total_records": len(debts),
        "data": debts
    }
@router.get("/owed-to-me/{user_id}", summary="Lấy danh sách các khoản người khác nợ tôi (theo nhóm hoặc tổng các nhóm)")
def api_get_debts_owed_to_me(
    user_id: int, 
    group_id: Optional[int] = Query(None, description="Mã nhóm quỹ (bỏ trống để lấy tổng tất cả các nhóm)"), 
    db: Session = Depends(get_db)
):
    """
    API trả về danh sách các khoản nợ mà người khác phải trả cho user_id.
    """
    debts = crud_debt.get_debts_owed_to_me(db, user_id=user_id, group_id=group_id)
    return {
        "user_id": user_id,
        "group_id": group_id if group_id else "all_groups",
        "total_records": len(debts),
        "data": debts
    }


@router.post("/payments", summary="Thành viên báo cáo đã chuyển khoản nợ")
def api_create_payment_request(
    payment_in: PaymentCreate,
    db: Session = Depends(get_db)
):
    """
    Thành viên báo cáo đã chuyển khoản (số tiền, ảnh minh chứng, phương thức).
    Hệ thống kiểm tra không cho phép trả vượt số nợ còn lại.
    """
    # Nếu trong dự án dùng user đăng nhập từ token, bạn thay user_id bằng user hiện tại. 
    # Tạm thời để user_id mặc định hoặc lấy từ body/token tùy theo dự án.
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