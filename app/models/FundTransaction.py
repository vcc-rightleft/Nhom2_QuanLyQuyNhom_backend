from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.session import Base


class TransactionType(str, enum.Enum):
    INCOME = "INCOME"   # THU
    EXPENSE = "EXPENSE" # CHI


class TransactionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"       # Giao dịch hiệu lực
    CANCELLED = "CANCELLED" # Giao dịch đã bị Host huỷ trong 24h


# Model Giao dịch quỹ (FundTransaction)
class FundTransaction(Base):
    __tablename__ = "fund_transactions"

    transaction_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    type = Column(String(20), nullable=False)  # INCOME hoặc EXPENSE
    amount = Column(BigInteger, nullable=False)  # Số tiền (VND)
    category = Column(String(100), nullable=True)  # Danh mục (VD: Ăn uống, Tiền quỹ...)
    payer_id = Column(BigInteger, nullable=True, index=True)  # Người nộp/chi
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    proof_image_url = Column(String(500), nullable=True)  # Ảnh chứng từ
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE hoặc CANCELLED
    created_by = Column(BigInteger, nullable=False)  # Người ghi
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    edit_logs = relationship(
        "FundTransactionLog",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="FundTransactionLog.log_id.desc()",
    )


# Model Lưu lịch sử sửa/huỷ giao dịch quỹ trong 24h (FundTransactionLog)
class FundTransactionLog(Base):
    __tablename__ = "fund_transaction_logs"

    log_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(
        BigInteger,
        ForeignKey("fund_transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(20), nullable=False)  # UPDATE (Sửa) hoặc CANCEL (Huỷ)
    changed_by = Column(BigInteger, nullable=False)  # ID của Host thực hiện
    reason = Column(Text, nullable=False)  # Lý do sửa/huỷ (bắt buộc)
    old_data = Column(Text, nullable=True)  # JSON dữ liệu trước khi sửa/huỷ
    new_data = Column(Text, nullable=True)  # JSON dữ liệu sau khi sửa/huỷ
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transaction = relationship("FundTransaction", back_populates="edit_logs")


# Model Đợt thu (Collection)
class Collection(Base):
    __tablename__ = "collections"

    collection_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    name = Column(String(200), nullable=False)  # Tên đợt thu
    amount_per_member = Column(BigInteger, nullable=False)  # Số tiền mỗi người
    due_date = Column(DateTime, nullable=True)  # Hạn nộp
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, COMPLETED, CANCELLED
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)