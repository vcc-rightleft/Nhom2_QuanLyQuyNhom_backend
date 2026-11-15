from sqlalchemy.orm import Session
from app.models.debt_payment import Debt, DebtStatusEnum
from fastapi import HTTPException
from app.models.debt_payment import Debt, Payment, PaymentStatusEnum, DebtStatusEnum
from app.schemas.debt_payment import PaymentCreate, PaymentReview

def create_debts(db: Session, group_id: int, source_type: str, debtor_id: int, payee_id: int, amount: float):
    """
    Tạo khoản nợ mới từ hóa đơn (INVOICE) hoặc đợt thu quỹ (COLLECTION_PERIOD).
    """
    db_debt = Debt(
        group_id=group_id,
        source_type=source_type,
        debtor_id=debtor_id,
        payee_id=payee_id,
        amount=amount,
        paid_amount=0.00,
        status=DebtStatusEnum.UNPAID
    )
    db.add(db_debt)
    db.commit()
    db.refresh(db_debt)
    return db_debt

def cancel_debts(db: Session, debt_id: int):
    """
    Hủy khoản nợ khi hóa đơn hoặc giao dịch gốc bị hủy.
    """
    db_debt = db.query(Debt).filter(Debt.id == debt_id).first()
    if db_debt:
        db.delete(db_debt)
        db.commit()
        return True
    return False

def get_debts_owed_by_me(db: Session, user_id: int, group_id: int = None):
    """
    API: Lấy danh sách các khoản tôi nợ người khác.
    Hỗ trợ lọc theo từng nhóm cụ thể (group_id) hoặc lấy tổng tất cả các nhóm (group_id = None).
    """
    query = db.query(Debt).filter(
        Debt.debtor_id == user_id, 
        Debt.status != DebtStatusEnum.PAID
    )
    if group_id is not None:
        query = query.filter(Debt.group_id == group_id)
    return query.all()

def get_debts_owed_to_me(db: Session, user_id: int, group_id: int = None):
    """
    API: Lấy danh sách các khoản người khác nợ tôi.
    Hỗ trợ lọc theo từng nhóm cụ thể (group_id) hoặc lấy tổng tất cả các nhóm (group_id = None).
    """
    query = db.query(Debt).filter(
        Debt.payee_id == user_id, 
        Debt.status != DebtStatusEnum.PAID
    )
    if group_id is not None:
        query = query.filter(Debt.group_id == group_id)
    return query.all()

def create_payment_request(db: Session, obj_in: PaymentCreate, user_id: int):
    """
    Thành viên báo cáo đã chuyển khoản (gửi số tiền, ảnh minh chứng).
    Kiểm tra không cho phép trả vượt số nợ còn lại.
    """
    debt = db.query(Debt).filter(Debt.id == obj_in.debt_id).first()
    if not debt:
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản nợ này.")
    
    current_paid = float(debt.paid_amount or 0.0)
    total_amount = float(debt.amount)
    remaining_amount = total_amount - current_paid

    if obj_in.amount > remaining_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Số tiền thanh toán ({obj_in.amount}) vượt quá số nợ còn lại ({remaining_amount})."
        )

    db_payment = Payment(
        debt_id=obj_in.debt_id,
        amount=obj_in.amount,
        payment_method=obj_in.payment_method,
        proof_image=obj_in.proof_image,
        status=PaymentStatusEnum.PENDING,
        confirmed_by=None
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


def review_payment_request(db: Session, payment_id: int, review_in: PaymentReview, reviewer_id: int):
    """
    Host hoặc người được trả xác nhận / từ chối thanh toán.
    Nếu CONFIRMED, tự động gạch nợ (cập nhật paid_amount và trạng thái nợ).
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu thanh toán này.")
    
    if payment.status != PaymentStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="Yêu cầu thanh toán này đã được xử lý trước đó.")

    if review_in.status not in ["CONFIRMED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Trạng thái xác nhận không hợp lệ (chỉ chấp nhận CONFIRMED hoặc REJECTED).")

    payment.status = PaymentStatusEnum(review_in.status)
    payment.confirmed_by = reviewer_id

    if payment.status == PaymentStatusEnum.CONFIRMED:
        debt = db.query(Debt).filter(Debt.id == payment.debt_id).first()
        if debt:
            current_paid = float(debt.paid_amount or 0.0)
            new_paid = current_paid + float(payment.amount)
            debt.paid_amount = new_paid

            if new_paid >= float(debt.amount):
                debt.status = DebtStatusEnum.PAID
            else:
                debt.status = DebtStatusEnum.PARTIAL

    db.commit()
    db.refresh(payment)
    return payment