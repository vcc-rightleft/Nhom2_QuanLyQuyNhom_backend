from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.session import Base

class TransactionType(str, enum.Enum):
    INCOME = "INCOME"   # THU
    EXPENSE = "EXPENSE" # CHI

# Model Giao dịch quỹ (FundTransaction)
class FundTransaction(Base):
    __tablename__ = "fund_transactions"

    transaction_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    type = Column(String(20), nullable=False) # INCOME hoac EXPENSE
    amount = Column(BigInteger, nullable=False) # So tien (VND)
    category = Column(String(100), nullable=True) # Danh muc (vi du: An uong, Tien quy...)
    payer_id = Column(BigInteger, nullable=True) # Nguoi nop/chi
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    proof_image_url = Column(String(500), nullable=True) # Anh chung tu
    created_by = Column(BigInteger, nullable=False) # Nguoi ghi
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# Model Dot thu (Collection)
class Collection(Base):
    __tablename__ = "collections"

    collection_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    name = Column(String(200), nullable=False) # Ten dot thu
    amount_per_member = Column(BigInteger, nullable=False) # So tien moi nguoi
    due_date = Column(DateTime, nullable=True) # Han nop
    status = Column(String(20), default="ACTIVE", nullable=False) # ACTIVE, COMPLETED, CANCELLED
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)