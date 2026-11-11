import enum
from sqlalchemy import Column, Integer, String, Numeric, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.db import Base  

class SourceTypeEnum(str, enum.Enum):
    INVOICE = "INVOICE"
    COLLECTION_PERIOD = "COLLECTION_PERIOD"

class DebtStatusEnum(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"

class PaymentStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"

class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, nullable=False)
    source_type = Column(Enum(SourceTypeEnum), nullable=False)
    debtor_id = Column(Integer, nullable=False)
    payee_id = Column(Integer, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    paid_amount = Column(Numeric(12, 2), default=0.00)
    status = Column(Enum(DebtStatusEnum), default=DebtStatusEnum.UNPAID)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    payments = relationship("Payment", back_populates="debt", cascade="all, delete-orphan")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    proof_image = Column(String(255), nullable=True)
    status = Column(Enum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING)
    confirmed_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    debt = relationship("Debt", back_populates="payments")