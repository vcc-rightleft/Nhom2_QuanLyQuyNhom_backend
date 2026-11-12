from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.user import User, SystemRole, UserStatus
from app.core.security import decode_access_token

try:
    from app.db.database import get_db
except ImportError:
    from app.db.session import get_db

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Lấy thông tin user từ JWT Token, chặn ngay nếu token sai hoặc tài khoản bị LOCKED."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
        )

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
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


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Chỉ cho phép Admin toàn hệ thống truy cập."""
    if current_user.role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền Quản trị viên (Admin).",
        )
    return current_user


def require_group_member(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Kiểm tra user hiện tại có phải thành viên ACTIVE của nhóm group_id không."""
    if current_user.role == SystemRole.ADMIN:
        return current_user

    query = text(
        "SELECT id FROM group_members "
        "WHERE group_id = :group_id AND user_id = :user_id AND status = 'ACTIVE'"
    )
    member = db.execute(query, {"group_id": group_id, "user_id": current_user.id}).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải thành viên của nhóm quỹ này.",
        )
    return current_user


def require_group_host(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Kiểm tra user hiện tại có phải Trưởng nhóm (HOST) của nhóm group_id không."""
    if current_user.role == SystemRole.ADMIN:
        return current_user

    query = text(
        "SELECT id FROM group_members "
        "WHERE group_id = :group_id AND user_id = :user_id "
        "AND role = 'HOST' AND status = 'ACTIVE'"
    )
    host = db.execute(query, {"group_id": group_id, "user_id": current_user.id}).first()
    if not host:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Trưởng nhóm (Host) mới có quyền thực hiện thao tác này.",
        )
    return current_user