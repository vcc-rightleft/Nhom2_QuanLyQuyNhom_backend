from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric
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
    bill_date = Column(DateTime, nullable=True, default=datetime.utcnow, index=True)
    total_amount = Column(Numeric(15, 2), nullable=False)

    # Hỗ trợ cả 2 tên cột người trả tiền của 2 nhánh
    paid_by = Column(Integer, nullable=True, index=True)
    payer_id = Column(Integer, nullable=True)

    split_type = Column(String(50), nullable=False)
    fee_split_mode = Column(String(50), nullable=True, default="EQUAL")
    items_subtotal = Column(Numeric(15, 2), nullable=True, default=0.00)
    service_ship_fee = Column(Numeric(15, 2), nullable=True, default=0.00)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE hoặc CANCELLED

    note = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    shares = relationship("BillShare", back_populates="bill", cascade="all, delete-orphan")