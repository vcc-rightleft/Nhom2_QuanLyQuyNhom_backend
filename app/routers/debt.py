from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import debt as crud_debt

router = APIRouter(prefix="/debts", tags=["Debts & Funds"])

@router.get("/owed-by-me/{user_id}")
def api_owed_by_me(user_id: int, group_id: int = None, db: Session = Depends(get_db)):
    """Lấy danh sách các khoản tôi nợ người khác"""
    return crud_debt.get_debts_owed_by_me(db, user_id=user_id, group_id=group_id)

@router.get("/owed-to-me/{user_id}")
def api_owed_to_me(user_id: int, group_id: int = None, db: Session = Depends(get_db)):
    """Lấy danh sách người khác nợ tôi"""
    return crud_debt.get_debts_owed_to_me(db, user_id=user_id, group_id=group_id)