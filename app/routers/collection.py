from datetime import datetime
from app.db.session import get_db  # Đường dẫn lấy session DB 
from app.models.Collection import CollectionCampaign, MemberDebt
from app.models.FundTransaction import (
    FundTransaction,
)  # Model giao dịch quỹ đã làm trước đó
# Giả định bạn có model Group và GroupMember chứa danh sách thành viên nhóm
# Thay thế bằng tên model thực tế trong project của bạn nếu cần:
from app.models.item import User  # Hoặc bảng GroupMember tương ứng
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import collection_schemas as schemas  # Hoặc import trực tiếp từ thư mục schemas

router = APIRouter(prefix="/api/collections", tags=["Collection & Debt Management"])


@router.post(
    "/", status_code=status.HTTP_201_CREATED
)  # Bỏ response_model nếu muốn trả về custom dict chứa cả danh sách công nợ
def create_collection_campaign(
    data: schemas.CollectionCreate, db: Session = Depends(get_db)
):
  """1. Tạo đợt thu (mỗi người đóng X đồng), tự động sinh danh sách

  ai đã đóng/chưa đóng và gọi module Công nợ tạo khoản phải đóng.
  """
  # 1. Tạo đợt thu mới
  new_collection = CollectionCampaign(
      group_id=data.group_id,
      name=data.name,
      amount_per_member=data.amount_per_member,
      created_by=data.created_by,
      status="ACTIVE",
  )
  db.add(new_collection)
  db.commit()
  db.refresh(new_collection)

  # 2. Lấy danh sách thành viên thuộc nhóm (group_id) để khởi tạo công nợ
  # (Giả định bạn lấy từ bảng User hoặc bảng thành viên nhóm)
  # Ví dụ mẫu truy vấn lấy user trong nhóm:
  members = db.query(User).all()  # Hoặc lọc theo group nếu có bảng liên kết

  created_debts = []
  for member in members:
    # Tránh trường hợp lấy nhầm id không tồn tại, tùy chỉnh theo cấu trúc bảng của bạn
    member_id = getattr(member, "id", getattr(member, "user_id", None))
    if not member_id:
      continue

    debt = MemberDebt(
        collection_id=new_collection.collection_id,
        user_id=member_id,
        amount_due=data.amount_per_member,
        status="UNPAID",  # Mặc định là chưa đóng
    )
    db.add(debt)
    created_debts.append(debt)

  db.commit()

  return {
      "message": (
          "Tạo đợt thu và khởi tạo danh sách khoản phải đóng thành công!"
      ),
      "collection_id": new_collection.collection_id,
      "total_members_assigned": len(created_debts),
  }


@router.post("/payments", status_code=status.HTTP_200_OK)
def record_member_payment(
    payment: schemas.RecordPaymentRequest, db: Session = Depends(get_db)
):
  """2. Host ghi nhận thành viên nộp quỹ (số tiền > 0):

  - Cập nhật trạng thái công nợ sang 'PAID' (Đã đóng).
  - Đồng thời ghi nhận vào bảng giao dịch quỹ (Fund Transaction - INCOME).
  """
  # Kiểm tra điều kiện số tiền > 0 theo đúng yêu cầu task
  if payment.amount <= 0:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Số tiền nộp quỹ phải lớn hơn 0!",
    )

  # Tìm khoản công nợ tương ứng của thành viên trong đợt thu
  debt_record = (
      db.query(MemberDebt)
      .filter(
          MemberDebt.collection_id == payment.collection_id,
          MemberDebt.user_id == payment.user_id,
      )
      .first()
  )

  if not debt_record:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Không tìm thấy thông tin công nợ của thành viên này trong đợt thu!",
    )

  # Cập nhật trạng thái công nợ thành đã đóng
  debt_record.status = "PAID"
  debt_record.paid_at = datetime.utcnow()

  # Đồng thời ghi nhận vào dòng tiền của quỹ chung (Fund Transaction)
  new_transaction = FundTransaction(
      group_id=1,  # Hoặc lấy group_id từ collection tương ứng
      type="INCOME",
      amount=payment.amount,
      category="Đóng quỹ đợt thu",
      payer_id=payment.user_id,
      description=(
          payment.description
          or f"Nộp tiền cho đợt thu ID: {payment.collection_id}"
      ),
      occurred_at=datetime.utcnow(),
      created_by=payment.user_id,
  )
  db.add(new_transaction)
  db.commit()

  return {
      "message": "Ghi nhận khoản thu và cập nhật công nợ thành công!",
      "user_id": payment.user_id,
      "amount_paid": payment.amount,
      "debt_status": "PAID",
  }