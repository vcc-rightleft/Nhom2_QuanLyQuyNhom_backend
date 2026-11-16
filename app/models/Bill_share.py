from sqlalchemy import Column, Integer, Numeric

from app.db.session import Base


class BillShare(Base):
    __tablename__ = "bill_shares"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    bill_id = Column(Integer, nullable=False)

    member_id = Column(Integer, nullable=False)

    amount = Column(Numeric(15, 0), nullable=False)