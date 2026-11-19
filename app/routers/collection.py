from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.models.FundTransaction import FundTransaction
from app.models.Calculate import get_group_fund_balance
from app.schemas.expense import (
    ExpenseCreateRequest,
    IncomeCreateRequest,
    ExpenseTransactionResponse,
    RecordExpenseResponse,
)

router = APIRouter(prefix="/expenses", tags=["Expense & Fund Balance Management"])


@router.post("/", response_model=RecordExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreateRequest,
    db: Session = Depends(get_db)
):
    if payload.role.upper() != "HOST":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Host mới có quyền thực hiện ghi khoản chi quỹ!"
        )

    if payload.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền chi phải lớn hơn 0!"
        )

    if not payload.category or not payload.category.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập danh mục khoản chi!"
        )

    if not payload.proof_image_url or not payload.proof_image_url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng đính kèm ảnh chứng từ cho khoản chi!"
        )

    try:
        current_fund = get_group_fund_balance(db, payload.group_id)
        current_balance = current_fund["balance"]

        if payload.amount > current_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số dư quỹ không đủ để chi! Số dư hiện tại: {current_balance:,} VND, số tiền muốn chi: {payload.amount:,} VND."
            )

        new_expense = FundTransaction(
            group_id=payload.group_id,
            type="EXPENSE",
            amount=payload.amount,
            category=payload.category.strip(),
            payer_id=payload.payer_id or payload.created_by,
            description=payload.description,
            occurred_at=datetime.utcnow(),
            proof_image_url=payload.proof_image_url.strip(),
            created_by=payload.created_by,
            created_at=datetime.utcnow(),
        )
        db.add(new_expense)
        db.flush()

        updated_fund = get_group_fund_balance(db, payload.group_id)
        db.commit()
        db.refresh(new_expense)

        return {
            "message": "Ghi nhận khoản chi thành công!",
            "transaction": new_expense,
            "fund_summary": updated_fund,
        }

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi thực hiện giao dịch: {str(e)}"
        )


@router.post("/income", response_model=RecordExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_income(
    payload: IncomeCreateRequest,
    db: Session = Depends(get_db)
):
    if payload.role.upper() != "HOST":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Host mới có quyền thực hiện ghi khoản thu quỹ!"
        )

    if payload.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền thu phải lớn hơn 0!"
        )

    try:
        new_income = FundTransaction(
            group_id=payload.group_id,
            type="INCOME",
            amount=payload.amount,
            category=(payload.category or "Thu quỹ chung").strip(),
            payer_id=payload.payer_id or payload.created_by,
            description=payload.description or "Thu bổ sung vào quỹ chung",
            occurred_at=datetime.utcnow(),
            proof_image_url=payload.proof_image_url.strip() if payload.proof_image_url else None,
            created_by=payload.created_by,
            created_at=datetime.utcnow(),
        )
        db.add(new_income)
        db.flush()

        updated_fund = get_group_fund_balance(db, payload.group_id)
        db.commit()
        db.refresh(new_income)

        return {
            "message": "Ghi nhận khoản thu vào quỹ chung thành công!",
            "transaction": new_income,
            "fund_summary": updated_fund,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi thực hiện giao dịch thu: {str(e)}"
        )


@router.get("/balance/{group_id}", status_code=status.HTTP_200_OK)
def get_balance(group_id: int, db: Session = Depends(get_db)):
    return get_group_fund_balance(db, group_id)


@router.get("/transactions/{group_id}", response_model=List[ExpenseTransactionResponse], status_code=status.HTTP_200_OK)
def get_transactions(group_id: int, db: Session = Depends(get_db)):
    return (
        db.query(FundTransaction)
        .filter(FundTransaction.group_id == group_id)
        .order_by(FundTransaction.transaction_id.desc())
        .all()
    )
