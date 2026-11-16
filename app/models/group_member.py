from sqlalchemy import Column, Integer, String

from app.db.session import Base


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    group_id = Column(Integer, nullable=False)

    user_id = Column(Integer, nullable=False)

    role = Column(String(20), default="MEMBER")

    status = Column(String(20), default="ACTIVE")