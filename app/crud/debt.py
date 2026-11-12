from sqlalchemy.orm import Session
from app.models.debt_payment import Debt, DebtStatusEnum

def create_debts(db: Session, group_id: int, source_type: str, debtor_id: int, payee_id: int, amount: float):
    """Hàm tạo khoản nợ mới từ hóa đơn hoặc đợt thu quỹ"""
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
    """Hàm hủy khoản nợ"""
    db_debt = db.query(Debt).filter(Debt.id == debt_id).first()
    if db_debt:
        db.delete(db_debt)
        db.commit()
        return True
    return False

def get_debts_owed_by_me(db: Session, user_id: int, group_id: int = None):
    """API: Tôi nợ ai bao nhiêu"""
    query = db.query(Debt).filter(Debt.debtor_id == user_id, Debt.status != DebtStatusEnum.PAID)
    if group_id:
        query = query.filter(Debt.group_id == group_id)
    return query.all()

def get_debts_owed_to_me(db: Session, user_id: int, group_id: int = None):
    """API: Ai nợ tôi bao nhiêu"""
    query = db.query(Debt).filter(Debt.payee_id == user_id, Debt.status != DebtStatusEnum.PAID)
    if group_id:
        query = query.filter(Debt.group_id == group_id)
    return query.all()