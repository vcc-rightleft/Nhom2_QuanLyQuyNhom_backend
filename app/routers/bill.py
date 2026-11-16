from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.bill import BillEqualSplitCreate, BillEqualSplitResponse
from app.crud.bill import create_equal_split_bill

router = APIRouter(prefix="/bills", tags=["Bills"])


@router.post("/equal-split", response_model=BillEqualSplitResponse, status_code=status.HTTP_201_CREATED)
def create_bill_equal_split_api(bill_in: BillEqualSplitCreate, db: Session = Depends(get_db)):
    """API tạo hoá đơn chia đều, tự động tạo khoản nợ và gửi thông báo."""
    try:
        return create_equal_split_bill(db=db, bill_in=bill_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))