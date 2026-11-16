from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.crud import debt as crud_debt

router = APIRouter(prefix="/debts", tags=["Debts & Funds Management"])

@router.get("/owed-by-me/{user_id}", summary="Lấy danh sách các khoản tôi nợ (theo nhóm hoặc tổng các nhóm)")
def api_get_debts_owed_by_me(
    user_id: int, 
    group_id: Optional[int] = Query(None, description="Mã nhóm quỹ (bỏ trống để lấy tổng tất cả các nhóm)"), 
    db: Session = Depends(get_db)
):
    """
    API trả về danh sách các khoản nợ mà user_id đang phải trả cho người khác.
    """
    debts = crud_debt.get_debts_owed_by_me(db, user_id=user_id, group_id=group_id)
    return {
        "user_id": user_id,
        "group_id": group_id if group_id else "all_groups",
        "total_records": len(debts),
        "data": debts
    }

@router.get("/owed-to-me/{user_id}", summary="Lấy danh sách các khoản người khác nợ tôi (theo nhóm hoặc tổng các nhóm)")
def api_get_debts_owed_to_me(
    user_id: int, 
    group_id: Optional[int] = Query(None, description="Mã nhóm quỹ (bỏ trống để lấy tổng tất cả các nhóm)"), 
    db: Session = Depends(get_db)
):
    """
    API trả về danh sách các khoản nợ mà người khác phải trả cho user_id.
    """
    debts = crud_debt.get_debts_owed_to_me(db, user_id=user_id, group_id=group_id)
    return {
        "user_id": user_id,
        "group_id": group_id if group_id else "all_groups",
        "total_records": len(debts),
        "data": debts
    }