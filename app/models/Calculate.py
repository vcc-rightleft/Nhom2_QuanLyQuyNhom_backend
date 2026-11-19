from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.FundTransaction import FundTransaction


def get_group_fund_balance(db: Session, group_id: int):
    # Tổng THU
    total_income = (
        db.query(func.coalesce(func.sum(FundTransaction.amount), 0))
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.type == "INCOME",
        )
        .scalar()
    )

    # Tổng CHI
    total_expense = (
        db.query(func.coalesce(func.sum(FundTransaction.amount), 0))
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.type == "EXPENSE",
        )
        .scalar()
    )

    income_int = int(total_income or 0)
    expense_int = int(total_expense or 0)
    balance = income_int - expense_int

    return {
        "group_id": group_id,
        "total_income": income_int,
        "total_expense": expense_int,
        "balance": balance,
    }