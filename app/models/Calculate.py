from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.FundTransaction import FundTransaction


def get_group_fund_balance(db: Session, group_id: int):
    active_filter = or_(
        FundTransaction.status == "ACTIVE",
        FundTransaction.status.is_(None),
    )

    # Tổng THU (chỉ tính các giao dịch đang hiệu lực, không tính giao dịch đã huỷ)
    total_income = (
        db.query(func.coalesce(func.sum(FundTransaction.amount), 0))
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.type == "INCOME",
            active_filter,
        )
        .scalar()
    )

    # Tổng CHI (chỉ tính các giao dịch đang hiệu lực, không tính giao dịch đã huỷ)
    total_expense = (
        db.query(func.coalesce(func.sum(FundTransaction.amount), 0))
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.type == "EXPENSE",
            active_filter,
        )
        .scalar()
    )

    total_income = int(total_income or 0)
    total_expense = int(total_expense or 0)
    balance = total_income - total_expense

    return {
        "group_id": group_id,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
    }
