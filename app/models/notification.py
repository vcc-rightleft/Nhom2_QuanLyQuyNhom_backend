from sqlalchemy import Column, Integer, String, Text, Boolean

from app.db.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    receiver_id = Column(Integer, nullable=False)

    type = Column(String(50), nullable=False)

    title = Column(String(255), nullable=False)

    content = Column(Text, nullable=False)

    link = Column(String(255), nullable=True)

    is_read = Column(Boolean, default=False)