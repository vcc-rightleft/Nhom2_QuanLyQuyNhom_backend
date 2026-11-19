import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.FundTransaction import FundTransaction
from app.models.fund_group import FundGroup
from app.schemas.statement import (
    CashflowStatementResponse,
    CategoryExpenseItem,
    DailyCashflowItem,
)

router = APIRouter(
    prefix="/statements",
    tags=["Cashflow Statement (Sao kê)"],
)


def _resolve_period(
    month: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> Tuple[str, Optional[str], date, date]:
    """
    Xác định kỳ sao kê theo tháng (YYYY-MM) hoặc khoảng ngày (start_date -> end_date).
    Nếu không truyền cả hai, mặc định lấy tháng hiện tại.
    """
    if month and (start_date is not None or end_date is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ chọn theo tháng (month) HOẶC theo khoảng ngày (start_date, end_date), không truyền đồng thời.",
        )

    if month:
        try:
            parts = month.strip().split("-")
            if len(parts) != 2:
                raise ValueError
            year = int(parts[0])
            month_num = int(parts[1])
            if not (1 <= month_num <= 12) or year < 1970 or year > 9999:
                raise ValueError
            last_day = calendar.monthrange(year, month_num)[1]
            normalized_month = f"{year:04d}-{month_num:02d}"
            return (
                "month",
                normalized_month,
                date(year, month_num, 1),
                date(year, month_num, last_day),
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tham số month không hợp lệ. Vui lòng dùng định dạng YYYY-MM (VD: 2026-11).",
            )

    if start_date is not None or end_date is not None:
        if start_date is None or end_date is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Khi lọc theo khoảng ngày, vui lòng truyền đầy đủ cả start_date và end_date.",
            )
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date không được lớn hơn end_date.",
            )
        return "date_range", None, start_date, end_date

    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    normalized_month = f"{today.year:04d}-{today.month:02d}"
    return (
        "month",
        normalized_month,
        date(today.year, today.month, 1),
        date(today.year, today.month, last_day),
    )


@router.get(
    "/groups/{group_id}",
    response_model=CashflowStatementResponse,
    status_code=status.HTTP_200_OK,
    summary="Sao kê dòng tiền theo kỳ (chọn tháng hoặc khoảng ngày)",
)
def get_cashflow_statement(
    group_id: int,
    month: Optional[str] = Query(
        None,
        description="Chọn kỳ theo tháng định dạng YYYY-MM (VD: 2026-11)",
    ),
    start_date: Optional[date] = Query(
        None,
        description="Ngày bắt đầu khoảng ngày (YYYY-MM-DD)",
    ),
    end_date: Optional[date] = Query(
        None,
        description="Ngày kết thúc khoảng ngày (YYYY-MM-DD)",
    ),
    include_empty_days: bool = Query(
        True,
        description="Có trả về cả những ngày không phát sinh giao dịch trong dòng tiền từng ngày hay không",
    ),
    db: Session = Depends(get_db),
):
    if group_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_id phải lớn hơn 0.",
        )

    has_any_group = db.query(FundGroup.id).first() is not None
    if has_any_group:
        group = db.query(FundGroup).filter(FundGroup.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy nhóm quỹ ID={group_id}.",
            )

    period_mode, normalized_month, resolved_start, resolved_end = _resolve_period(
        month=month,
        start_date=start_date,
        end_date=end_date,
    )

    start_dt = datetime.combine(resolved_start, time.min)
    end_dt = datetime.combine(resolved_end, time.max)

    active_filter = or_(
        FundTransaction.status.is_(None),
        FundTransaction.status != "CANCELLED",
    )

    # 1. Tính số dư đầu kỳ (tất cả giao dịch hiệu lực xảy ra trước start_dt)
    prior_income = (
        db.query(func.coalesce(func.sum(FundTransaction.amount), 0))
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.type == "INCOME",
            FundTransaction.occurred_at < start_dt,
            active_filter,
        )
        .scalar()
    )
    prior_expense = (
        db.query(func.coalesce(func.sum(FundTransaction.amount), 0))
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.type == "EXPENSE",
            FundTransaction.occurred_at < start_dt,
            active_filter,
        )
        .scalar()
    )
    opening_balance = int(prior_income or 0) - int(prior_expense or 0)

    # 2. Lấy toàn bộ giao dịch hiệu lực trong kỳ [start_dt, end_dt]
    period_transactions: List[FundTransaction] = (
        db.query(FundTransaction)
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.occurred_at >= start_dt,
            FundTransaction.occurred_at <= end_dt,
            active_filter,
        )
        .order_by(FundTransaction.occurred_at.asc(), FundTransaction.transaction_id.asc())
        .all()
    )

    total_income = 0
    total_expense = 0
    category_totals: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"total_expense": 0, "transaction_count": 0}
    )
    daily_buckets: Dict[date, Dict[str, int]] = defaultdict(
        lambda: {"total_income": 0, "total_expense": 0, "transaction_count": 0}
    )

    for tx in period_transactions:
        amount = int(tx.amount or 0)
        tx_type = (tx.type or "").upper()
        tx_day = tx.occurred_at.date() if tx.occurred_at else resolved_start

        daily_buckets[tx_day]["transaction_count"] += 1

        if tx_type == "INCOME":
            total_income += amount
            daily_buckets[tx_day]["total_income"] += amount
        elif tx_type == "EXPENSE":
            total_expense += amount
            daily_buckets[tx_day]["total_expense"] += amount

            cat_name = (tx.category or "").strip() or "Chưa phân loại"
            category_totals[cat_name]["total_expense"] += amount
            category_totals[cat_name]["transaction_count"] += 1

    net_change = total_income - total_expense
    closing_balance = opening_balance + net_change

    # 3. Tổng hợp chi theo danh mục (sắp xếp giảm dần theo số tiền chi)
    expense_by_category: List[CategoryExpenseItem] = []
    for cat_name, stats in sorted(
        category_totals.items(),
        key=lambda item: (-item[1]["total_expense"], item[0]),
    ):
        pct = (
            round((stats["total_expense"] / total_expense) * 100, 2)
            if total_expense > 0
            else 0.0
        )
        expense_by_category.append(
            CategoryExpenseItem(
                category=cat_name,
                total_expense=stats["total_expense"],
                transaction_count=stats["transaction_count"],
                percentage=pct,
            )
        )

    # 4. Tổng hợp dòng tiền từng ngày kèm số dư luỹ kế
    daily_cashflow: List[DailyCashflowItem] = []
    running_balance = opening_balance
    current_day = resolved_start

    while current_day <= resolved_end:
        bucket = daily_buckets.get(current_day)
        day_income = bucket["total_income"] if bucket else 0
        day_expense = bucket["total_expense"] if bucket else 0
        day_count = bucket["transaction_count"] if bucket else 0
        day_net = day_income - day_expense
        running_balance += day_net

        if include_empty_days or day_count > 0:
            daily_cashflow.append(
                DailyCashflowItem(
                    date=current_day,
                    total_income=day_income,
                    total_expense=day_expense,
                    net_change=day_net,
                    closing_balance=running_balance,
                    transaction_count=day_count,
                )
            )
        current_day += timedelta(days=1)

    return CashflowStatementResponse(
        group_id=group_id,
        period_mode=period_mode,
        month=normalized_month,
        start_date=resolved_start,
        end_date=resolved_end,
        opening_balance=opening_balance,
        total_income=total_income,
        total_expense=total_expense,
        net_change=net_change,
        closing_balance=closing_balance,
        total_transactions=len(period_transactions),
        expense_by_category=expense_by_category,
        daily_cashflow=daily_cashflow,
    )