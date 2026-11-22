from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
from app.db.session import Base


class BillShare(Base):
    __tablename__ = "bill_shares"
    bill = relationship("Bill", back_populates="shares")
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(Integer, nullable=False, index=True)
    amount = Column(Numeric(15, 0), nullable=False)
    debt_id = Column(Integer, nullable=True, index=True)  # Liên kết tới khoản nợ trong bảng debts