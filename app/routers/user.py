from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserProfileOut, UserProfileUpdate, ChangePasswordRequest
from app.crud.user import update_user_profile, change_user_password, invalidate_user_tokens
from app.routers.auth import get_current_user  # Đổi lại nếu nhóm để get_current_user ở file khác

router = APIRouter(prefix="/api/users", tags=["Users & Profile"])


@router.get("/me", response_model=UserProfileOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Lấy thông tin hồ sơ & tài khoản ngân hàng nhận tiền của người dùng hiện tại"""
    return current_user


@router.put("/me", response_model=UserProfileOut)
def update_my_profile(
    profile_in: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật họ tên, SĐT, avatar và thông tin ngân hàng nhận tiền"""
    return update_user_profile(db=db, current_user=current_user, profile_in=profile_in)


@router.put("/me/password")
def update_my_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đổi mật khẩu (kiểm tra mật khẩu cũ + vô hiệu hóa token cũ)"""
    return change_user_password(db=db, current_user=current_user, payload=payload)


@router.post("/logout")
def logout_and_revoke_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Vô hiệu hóa JWT token ngay lập tức khi đăng xuất"""
    return invalidate_user_tokens(db=db, current_user=current_user)