"""Authenticated notification endpoints: user id comes exclusively from verified JWT."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.routers.auth import get_current_user
from app.models.user import User
from app.crud import notification as crud_notif
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationResponse])
def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud_notif.get_user_notifications(db, user_id=current_user.id, skip=skip, limit=limit, unread_only=unread_only)

@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"unread_count": crud_notif.count_unread_notifications(db, user_id=current_user.id)}

# Define static read-all route separately from individual notification route.
@router.put("/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud_notif.mark_all_as_read(db, user_id=current_user.id)

@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_single_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = crud_notif.mark_as_read(db, notification_id=notification_id, user_id=current_user.id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo của tài khoản này")
    return notif
