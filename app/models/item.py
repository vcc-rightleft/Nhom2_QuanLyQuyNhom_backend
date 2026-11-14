from sqlalchemy import Column, Integer, String, Text, BigInteger
from app.db.session import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(BigInteger, default=0)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    group_id = Column(Integer, nullable=False, default=1, index=True)
    full_name = Column(String(255), nullable=False)
    student_code = Column(String(50), nullable=True)
    role = Column(String(50), nullable=False, default="MEMBER")  # HOST hoặc MEMBER
