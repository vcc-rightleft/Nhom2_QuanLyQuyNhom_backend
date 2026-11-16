from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.models.user import User, SystemRole, UserStatus
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.user import UserResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

# Import hàm get_db từ file cấu hình database của nhóm bạn
try:
    from app.db.database import get_db
except ImportError:
    from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])
security_scheme = HTTPBearer()


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

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại.",
        )

    if user.status == UserStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tài khoản đã bị khóa. Lý do: {user.lock_reason or 'Vi phạm quy định'}",
        )
    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới (trùng email trả 409, mật khẩu bcrypt)",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email này đã được sử dụng (409 Conflict).",
        )

    new_user = User(
        email=email_clean,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        avatar_url=f"https://ui-avatars.com/api/?name={payload.full_name.strip()}&background=1E3A8A&color=fff",
        bank_name=payload.bank_name,
        bank_account_no=payload.bank_account_no,
        bank_account_name=payload.bank_account_name or payload.full_name.strip().upper(),
        role=SystemRole.USER,
        status=UserStatus.ACTIVE,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập trả về JWT Access Token",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
        )

    if user.status == UserStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tài khoản đã bị khóa. Lý do: {user.lock_reason or 'Vi phạm quy định'}",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    return TokenResponse(access_token=access_token, user=user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin người dùng hiện tại từ JWT Token",
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user