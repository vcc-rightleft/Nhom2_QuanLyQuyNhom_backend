from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.session import Base


class FundGroup(Base):
    __tablename__ = "fund_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    invite_code = Column(String(8), unique=True, nullable=False)
    status = Column(String(20), default="ACTIVE")
    creator_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)