from datetime import datetime
from app.db.session import Base  # Hoặc đường dẫn Base tùy thuộc vào project của bạn
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class CollectionCampaign(Base):
  __tablename__ = "collection_campaigns"

  collection_id = Column(
      Integer, primary_key=True, index=True, autoincrement=True
  )
  group_id = Column(
      Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
  )
  name = Column(String(255), nullable=False)
  amount_per_member = Column(Float, nullable=False)  # X đồng định mức
  status = Column(
      String(50), default="ACTIVE", nullable=False
  )  # ACTIVE, CLOSED
  created_by = Column(
      Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
  )
  created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

  # Quan hệ
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
  user_id = Column(
      Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
  )
  amount_due = Column(Float, nullable=False)
  status = Column(
      String(50), default="UNPAID", nullable=False
  )  # UNPAID (chưa đóng) / PAID (đã đóng)
  paid_at = Column(DateTime, nullable=True)

  # Quan hệ
  collection = relationship("CollectionCampaign", back_populates="debts")