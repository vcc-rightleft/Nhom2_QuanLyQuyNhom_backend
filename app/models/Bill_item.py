from sqlalchemy import Column, Integer, String, Numeric

from app.db.session import Base


class BillItem(Base):
    __tablename__ = "bill_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    bill_id = Column(Integer, nullable=False)

    name = Column(String(255), nullable=False)

    unit_price = Column(Numeric(15, 0), nullable=False)

    quantity = Column(Integer, nullable=False)

    consumer_user_ids = Column(String(255), nullable=True)