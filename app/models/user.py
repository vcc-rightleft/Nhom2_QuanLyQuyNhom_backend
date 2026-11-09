import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import declarative_base

# Nếu trong Backend/app/db của bạn đã có sẵn Base (ví dụ: from app.db.base import Base)
# thì bạn có thể import Base từ đó. Ở đây dùng declarative_base() tương thích độc lập:
try:
    from app.db.database import Base
except ImportError:
    Base = declarative_base()


class SystemRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    # Lưu ý: Host là vai trò trong từng nhóm (module Nhóm quỹ), không phải role hệ thống.


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Thông tin ngân hàng + số tài khoản nhận tiền khi thành viên trả nợ
    bank_name = Column(String(100), nullable=True)
    bank_account_no = Column(String(50), nullable=True)
    bank_account_name = Column(String(150), nullable=True)

    # Role hệ thống (USER/ADMIN) và Trạng thái (ACTIVE/LOCKED)
    role = Column(Enum(SystemRole), nullable=False, default=SystemRole.USER)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    lock_reason = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )