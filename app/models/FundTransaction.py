from datetime import datetime
import enum
from sqlalchemy import BigInteger, Column, DateTime, String, Text
from app.db.session import Base


class TransactionType(str, enum.Enum):
    INCOME = "INCOME"   # THU
    EXPENSE = "EXPENSE" # CHI


class FundTransaction(Base):
    __tablename__ = "fund_transactions"

    transaction_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    type = Column(String(20), nullable=False)  # INCOME hoặc EXPENSE
    amount = Column(BigInteger, nullable=False)  # Số tiền (VND)
    category = Column(String(100), nullable=True)  # Danh mục (VD: Ăn uống, Tiền quỹ...)
    payer_id = Column(BigInteger, nullable=True, index=True)  # Người nộp/chi
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    proof_image_url = Column(String(500), nullable=True)  # Ảnh chứng từ
    created_by = Column(BigInteger, nullable=False, default=1)  # Người ghi
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)