from sqlalchemy.orm import Session
from app.models.debt_payment import Debt, DebtStatusEnum

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