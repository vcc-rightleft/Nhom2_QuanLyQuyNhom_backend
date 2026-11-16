from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

class TransactionType(str, enum.Enum):
    INCOME = "INCOME"   # THU
    EXPENSE = "EXPENSE" # CHI

# Model Giao dịch quỹ (FundTransaction)
class FundTransaction(Base):
    __tablename__ = "fund_transactions"

    transaction_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    group_id = Column(BigInteger, ForeignKey("fund_groups.group_id"), nullable=False)
    type = Column(String(20), nullable=False) # INCOME hoac EXPENSE
    amount = Column(BigInteger, nullable=False) # So tien (VND)
    category = Column(String(100), nullable=True) # Danh muc (vi du: An uong, Tieng quy...)
    payer_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=True) # Nguoi nop/chi
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    proof_image_url = Column(String(500), nullable=True) # Anh chung tu
    created_by = Column(BigInteger, ForeignKey("users.user_id"), nullable=False) # Nguoi ghi
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships (neu can truy van)
    group = relationship("FundGroup", back_populates="transactions")
    creator = relationship("User", foreign_keys=[created_by])
    payer = relationship("User", foreign_keys=[payer_id])

# Model Dot thu (Collection)
class Collection(Base):
    __tablename__ = "collections"

    collection_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    group_id = Column(BigInteger, ForeignKey("fund_groups.group_id"), nullable=False)
    name = Column(String(200), nullable=False) # Ten dot thu
    amount_per_member = Column(BigInteger, nullable=False) # So tien moi nguoi
    due_date = Column(DateTime, nullable=True) # Han nop
    status = Column(String(20), default="ACTIVE", nullable=False) # ACTIVE, COMPLETED, CANCELLED
    created_by = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)