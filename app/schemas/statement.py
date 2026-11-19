from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class CategoryExpenseItem(BaseModel):
    category: str
    total_expense: int
    transaction_count: int
    percentage: float


class DailyCashflowItem(BaseModel):
    date: date
    total_income: int
    total_expense: int
    net_change: int
    closing_balance: int
    transaction_count: int


class CashflowStatementResponse(BaseModel):
    group_id: int
    period_mode: str  # "month" hoặc "date_range"
    month: Optional[str] = None
    start_date: date
    end_date: date
    opening_balance: int
    total_income: int
    total_expense: int
    net_change: int
    closing_balance: int
    total_transactions: int
    expense_by_category: List[CategoryExpenseItem]
    daily_cashflow: List[DailyCashflowItem]