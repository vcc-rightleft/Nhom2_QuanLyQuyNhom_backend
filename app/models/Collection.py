from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.db.session import Base


class CollectionCampaign(Base):
    __tablename__ = "collection_campaigns"

    collection_id = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    group_id = Column(Integer, nullable=False, index=True, default=1)
    name = Column(String(255), nullable=False)
    amount_per_member = Column(Float, nullable=False)  # X đồng định mức mỗi người
    due_date = Column(String(50), nullable=True)  # Hạn đóng (YYYY-MM-DD)
    status = Column(
        String(50), default="ACTIVE", nullable=False
    )  # ACTIVE, CLOSED
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Quan hệ với danh sách đóng quỹ của từng thành viên
    debts = relationship(
        "MemberDebt", back_populates="collection", cascade="all, delete-orphan"
    )


class MemberDebt(Base):
    __tablename__ = "member_debts"

    debt_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    collection_id = Column(
        Integer,
        ForeignKey("collection_campaigns.collection_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, nullable=False, index=True)
    member_name = Column(String(255), nullable=True)
    role = Column(String(50), default="MEMBER", nullable=True)
    amount_due = Column(Float, nullable=False)
    status = Column(
        String(50), default="UNPAID", nullable=False
    )  # UNPAID (chưa đóng) / PAID (đã đóng)
    paid_at = Column(DateTime, nullable=True)

    # Quan hệ ngược lại đợt thu
    collection = relationship("CollectionCampaign", back_populates="debts")
