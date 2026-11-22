from sqlalchemy.orm import Session
from app.models.notification import Notification

def create_notification(db: Session, user_id: int, title: str, message: str):
    """Hàm tiện ích để các module khác gọi trực tiếp khi phát sinh sự kiện"""
    db_obj = Notification(user_id=user_id, title=title, message=message)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_user_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 20, unread_only: bool = False):
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(skip).limit(limit).all()

def count_unread_notifications(db: Session, user_id: int) -> int:
    return db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).count()

def mark_as_read(db: Session, notification_id: int, user_id: int):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif

def mark_all_as_read(db: Session, user_id: int):
    db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).update({Notification.is_read: True})
    db.commit()
    return {"status": "success", "message": "All notifications marked as read"}