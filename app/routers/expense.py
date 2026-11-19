from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.models.FundTransaction import FundTransaction
from app.models.Calculate import get_group_fund_balance
from app.schemas.expense import ExpenseCreateRequest, RecordExpenseResponse

router = APIRouter(prefix="/expenses", tags=["Expense Management"])


@router.post("/", response_model=RecordExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Host ghi nhận khoản chi kèm danh mục và ảnh chứng từ:
    - Kiểm tra số tiền > 0, bắt buộc có danh mục và ảnh chứng từ.
    - Tính số dư hiện tại và chặn nếu chi vượt số dư quỹ.
    - Ghi giao dịch chi (EXPENSE) và tính lại số dư mới trong cùng một DB transaction.
    """
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
        # 1. Tính số dư hiện tại của nhóm trong cùng phiên transaction
        current_fund = get_group_fund_balance(db, payload.group_id)
        current_balance = current_fund["balance"]

        # 2. Kiểm tra không cho phép chi vượt số dư
        if payload.amount > current_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số dư quỹ không đủ để chi! Số dư hiện tại: {current_balance:,} VND, số tiền muốn chi: {payload.amount:,} VND."
            )

        # 3. Ghi nhận giao dịch khoản chi (EXPENSE)
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
        db.flush()  # Đẩy dữ liệu xuống DB trong transaction để tính lại số dư ngay lập tức

        # 4. Tính lại số dư mới sau khi ghi khoản chi trong cùng một transaction
        updated_fund = get_group_fund_balance(db, payload.group_id)

        # 5. Commit toàn bộ transaction
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


@router.get("/balance/{group_id}", status_code=status.HTTP_200_OK)
def get_balance(group_id: int, db: Session = Depends(get_db)):
    """API kiểm tra số dư hiện tại của nhóm quỹ."""
    return get_group_fund_balance(db, group_id)