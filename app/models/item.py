from sqlalchemy import Column, Integer, String, Text, BigInteger
from app.db.session import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(BigInteger, default=0)