
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.user import User, SystemRole, UserStatus
from app.models.fund_group import FundGroup
from app.core.security import decode_access_token

try:
    from app.db.database import get_db
except ImportError:
    from app.db.session import get_db


security_scheme = HTTPBearer()


# ==========================================================
# 1. XAC THUC JWT
# ==========================================================

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

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Token không hợp lệ"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại.",
        )

    try:
        token_version = int(payload.get("tv", -1))

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Token không hợp lệ"
        )

    if token_version != int(user.token_version or 0):
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập đã bị thu hồi"
        )

    if user.status == UserStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Tài khoản đã bị khóa. Lý do: "
                + (user.lock_reason or "Vi phạm quy định")
            ),
        )

    return user


# ==========================================================
# 2. KIEM TRA QUYEN ADMIN
# ==========================================================

def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:

    if current_user.role != SystemRole.ADMIN:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền Quản trị viên (Admin).",
        )

    return current_user


# ==========================================================
# 3. KIEM TRA NHOM CON HOAT DONG
# ==========================================================

def ensure_group_active(
    db: Session,
    group_id: int
) -> FundGroup:

    group = db.query(FundGroup).filter(
        FundGroup.id == group_id
    ).first()

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhóm quỹ."
        )

    group_status = str(
        group.status or ""
    ).strip().upper()

    if (
        group.deleted_at is not None
        or group_status in ("DELETED", "SOFT_DELETED")
    ):
        raise HTTPException(
            status_code=410,
            detail="Nhóm quỹ đã bị xóa mềm và không thể thực hiện thao tác."
        )

    if group_status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Nhóm quỹ hiện không ở trạng thái hoạt động."
        )

    return group


# ==========================================================
# 4. KIEM TRA QUYEN THANH VIEN
# ==========================================================

def require_group_member(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:

    # Kiểm tra nhóm trước khi kiểm tra quyền
    ensure_group_active(db, group_id)

    if current_user.role == SystemRole.ADMIN:
        return current_user

    query = text(
        "SELECT id FROM group_members "
        "WHERE group_id = :group_id "
        "AND user_id = :user_id "
        "AND status = 'ACTIVE'"
    )

    member = db.execute(
        query,
        {
            "group_id": group_id,
            "user_id": current_user.id
        }
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải thành viên của nhóm quỹ này.",
        )

    return current_user


# ==========================================================
# 5. KIEM TRA QUYEN HOST
# ==========================================================

def require_group_host(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:

    # Không cho thao tác trên nhóm đã xóa mềm
    ensure_group_active(db, group_id)

    if current_user.role == SystemRole.ADMIN:
        return current_user

    query = text(
        "SELECT id FROM group_members "
        "WHERE group_id = :group_id "
        "AND user_id = :user_id "
        "AND role = 'HOST' "
        "AND status = 'ACTIVE'"
    )

    host = db.execute(
        query,
        {
            "group_id": group_id,
            "user_id": current_user.id
        }
    ).first()

    if not host:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Chỉ Trưởng nhóm (Host) mới có quyền "
                "thực hiện thao tác này."
            ),
        )

    return current_user
