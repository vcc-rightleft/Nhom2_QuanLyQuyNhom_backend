from sqlalchemy.orm import Session
from sqlalchemy import func

def get_group_fund_balance(db: Session, group_id: int):
    # Tong THU
    total_income = db.query(func.coalesce(func.sum(FundTransaction.amount), 0))\
        .filter(FundTransaction.group_id == group_id, FundTransaction.type == "INCOME")\
        .scalar()
        
    # Tong CHI
    total_expense = db.query(func.coalesce(func.sum(FundTransaction.amount), 0))\
        .filter(FundTransaction.group_id == group_id, FundTransaction.type == "EXPENSE")\
        .scalar()
        
    balance = total_income - total_expense
    
    return {
        "group_id": group_id,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance
    }