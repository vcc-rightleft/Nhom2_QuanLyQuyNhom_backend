from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base


class SplitTypeEnum(str, enum.Enum):
    EQUAL = "EQUAL"          # Chia đều
    ITEMIZED = "ITEMIZED"    # Chia theo món ăn
    CUSTOM = "CUSTOM"        # Chia tuỳ chỉnh


class FeeSplitModeEnum(str, enum.Enum):
    EQUAL = "EQUAL"                # Phí ship/phục vụ chia đều
    PROPORTIONAL = "PROPORTIONAL"  # Phí ship/phục vụ chia theo tỉ lệ tiền món


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    payer_id = Column(Integer, nullable=False)  # Người ứng tiền thanh toán hoá đơn (chủ nợ)
    split_type = Column(String(50), nullable=False)  # ITEMIZED hoặc CUSTOM
    fee_split_mode = Column(String(50), nullable=True, default="EQUAL")  # EQUAL hoặc PROPORTIONAL
    items_subtotal = Column(Numeric(12, 2), nullable=False, default=0.00)
    service_ship_fee = Column(Numeric(12, 2), nullable=False, default=0.00)
    total_amount = Column(Numeric(12, 2), nullable=False)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    shares = relationship("BillShare", back_populates="bill", cascade="all, delete-orphan")


class BillItem(Base):
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    participant_ids = Column(String(500), nullable=False)  # Chuỗi ID người dùng món (VD: "1,2,3")

    bill = relationship("Bill", back_populates="items")


class BillShare(Base):
    __tablename__ = "bill_shares"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    items_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    fee_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    total_share_amount = Column(Numeric(12, 2), nullable=False)
    debt_id = Column(Integer, nullable=True)  # ID khoản nợ tương ứng trong bảng debts

    bill = relationship("Bill", back_populates="shares")
