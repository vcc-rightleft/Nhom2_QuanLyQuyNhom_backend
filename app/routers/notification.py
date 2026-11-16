from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.crud import notification as crud_notif
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationResponse])
def list_notifications(user_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """API lấy danh sách thông báo"""
    return crud_notif.get_user_notifications(db, user_id=user_id, skip=skip, limit=limit)

@router.get("/unread-count", response_model=dict)
def get_unread_count(user_id: int, db: Session = Depends(get_db)):
    """API lấy số lượng thông báo chưa đọc"""
    count = crud_notif.count_unread_notifications(db, user_id=user_id)
    return {"unread_count": count}

@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_single_read(notification_id: int, user_id: int, db: Session = Depends(get_db)):
    """API đánh dấu 1 thông báo là đã đọc"""
    notif = crud_notif.mark_as_read(db, notification_id=notification_id, user_id=user_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif

@router.put("/read-all", response_model=dict)
def mark_all_read(user_id: int, db: Session = Depends(get_db)):
    """API đánh dấu đọc tất cả thông báo"""
    return crud_notif.mark_all_as_read(db, user_id=user_id)