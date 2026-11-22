
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.crud.user import invalidate_user_tokens
from app.models.user import User, SystemRole, UserStatus
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.user import UserResponse

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

# Lấy kết nối database
from app.db.session import get_db


router = APIRouter(prefix="/auth", tags=["Auth"])
security_scheme = HTTPBearer()


# ==========================================
# XÁC THỰC NGƯỜI DÙNG TỪ JWT
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
        )

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ.",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại.",
        )

    # Kiểm tra phiên đăng nhập đã bị thu hồi chưa
    token_version = payload.get("tv")
    current_version = int(user.token_version or 0)

    if token_version is None or str(token_version) != str(current_version):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã bị thu hồi hoặc không hợp lệ.",
        )

    # Kiểm tra trạng thái tài khoản
    if user.status == UserStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Tài khoản đã bị khóa. "
                f"Lý do: {user.lock_reason or 'Vi phạm quy định'}"
            ),
        )

    return user


# ==========================================
# ĐĂNG KÝ TÀI KHOẢN
# ==========================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):

    email_clean = payload.email.strip().lower()

    existing_user = db.query(User).filter(
        User.email == email_clean
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email này đã được sử dụng.",
        )

    clean_name = payload.full_name.strip()
    encoded_name = quote(clean_name)

    new_user = User(
        email=email_clean,
        password_hash=hash_password(payload.password),
        full_name=clean_name,
        phone=payload.phone,
        avatar_url=(
            "https://ui-avatars.com/api/"
            f"?name={encoded_name}&background=1E3A8A&color=fff"
        ),
        bank_name=payload.bank_name,
        bank_account_no=payload.bank_account_no,
        bank_account_name=(
            payload.bank_account_name or clean_name.upper()
        ),
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ==========================================
# ĐĂNG NHẬP
# ==========================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập trả về JWT Access Token",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):

    email_clean = payload.email.strip().lower()

    user = db.query(User).filter(
        User.email == email_clean
    ).first()

    if not user or not verify_password(
        payload.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
        )

    if user.status == UserStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Tài khoản đã bị khóa. "
                f"Lý do: {user.lock_reason or 'Vi phạm quy định'}"
            ),
        )

    role_value = (
        user.role.value
        if hasattr(user.role, "value")
        else str(user.role)
    )

    # Giữ token_version để hỗ trợ thu hồi JWT khi đăng xuất
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": role_value,
            "tv": int(user.token_version or 0),
        }
    )

    return TokenResponse(
        access_token=access_token,
        user=user,
    )


# ==========================================
# THÔNG TIN TÀI KHOẢN
# ==========================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin người dùng hiện tại",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ==========================================
# ĐĂNG XUẤT
# ==========================================

@router.post(
    "/logout",
    summary="Đăng xuất và vô hiệu hóa JWT Token hiện tại",
)
def logout_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return invalidate_user_tokens(
        db=db,
        current_user=current_user,
    )
