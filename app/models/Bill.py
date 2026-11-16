from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric
from app.db.session import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    bill_date = Column(DateTime, nullable=False)
    total_amount = Column(Numeric(15, 0), nullable=False)
    paid_by = Column(Integer, nullable=False)
    split_type = Column(String(20), nullable=False)
    note = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)