import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserProfileUpdate, ChangePasswordRequest


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def update_user_profile(db: Session, current_user: User, profile_in: UserProfileUpdate) -> User:
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


def change_user_password(db: Session, current_user: User, payload: ChangePasswordRequest) -> dict:
    # 1. Kiểm tra mật khẩu cũ (Sửa thành password_hash thay vì hashed_password)
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không chính xác."
        )

    # 2. Chặn đặt trùng mật khẩu cũ
    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới không được trùng với mật khẩu hiện tại."
        )

    # 3. Lưu password_hash mới
    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.token_version = int(current_user.token_version or 0) + 1

    db.commit()
    db.refresh(current_user)
    return {"message": "Đổi mật khẩu thành công."}

def invalidate_user_tokens(db: Session, current_user: User) -> dict:
    current_user.token_version = int(current_user.token_version or 0) + 1
    db.commit()
    return {"message": "Đã thu hồi các token đăng nhập trước đó."}
