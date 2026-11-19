<<<<<<< HEAD
from sqlalchemy.orm import Session
from app.models.Bill import Bill
from app.models.Bill_share import BillShare
from app.models.notification import Notification
from app.schemas.bill import BillEqualSplitCreate
from app.crud.debt import create_debts


def calculate_equal_split(total_amount: int, participant_ids: list[int], payer_id: int) -> dict[int, int]:
    """
    Chia đều tổng tiền cho danh sách người tham gia, làm tròn xuống đến 1.000đ,
    phần dư dồn cho người trả trước (payer_id).
    """
    if not participant_ids:
        raise ValueError("Danh sách người tham gia không được rỗng")
    if total_amount <= 0:
        raise ValueError("Tổng tiền phải lớn hơn 0")

    unique_participants = list(dict.fromkeys(participant_ids))
    n = len(unique_participants)

    base_share = (int(total_amount) // n // 1000) * 1000
    remainder = int(total_amount) - (base_share * n)

    shares = {uid: base_share for uid in unique_participants}
    if payer_id in shares:
        shares[payer_id] += remainder
    else:
        shares[unique_participants[0]] += remainder

    return shares


def create_equal_split_bill(db: Session, bill_in: BillEqualSplitCreate) -> dict:
    # 1. Tính toán chia đều
    shares_map = calculate_equal_split(
        total_amount=bill_in.total_amount,
        participant_ids=bill_in.participant_ids,
        payer_id=bill_in.paid_by
    )

    # 2. Lưu hoá đơn vào bảng bills
    db_bill = Bill(
        group_id=bill_in.group_id,
        title=bill_in.title,
        bill_date=bill_in.bill_date,
        total_amount=bill_in.total_amount,
        paid_by=bill_in.paid_by,
        split_type="EQUAL",
        note=bill_in.note,
        image_url=bill_in.image_url
    )
    db.add(db_bill)
    db.commit()
    db.refresh(db_bill)

    # 3. Lưu BillShare bằng cách tự động dò tên cột khóa ngoại của nhóm
    shares_out = []
    for uid, share_amount in shares_map.items():
        share_kwargs = {"bill_id": db_bill.id}
        
        # Tự động gán đúng tên cột user/member trong BillShare của nhóm
        if hasattr(BillShare, "user_id"):
            share_kwargs["user_id"] = uid
        elif hasattr(BillShare, "member_id"):
            share_kwargs["member_id"] = uid
        elif hasattr(BillShare, "account_id"):
            share_kwargs["account_id"] = uid
        else:
            share_kwargs["user_id"] = uid # Fallback mặc định

        # Tự động gán đúng tên cột số tiền trong BillShare
        if hasattr(BillShare, "amount"):
            share_kwargs["amount"] = share_amount
        elif hasattr(BillShare, "share_amount"):
            share_kwargs["share_amount"] = share_amount

        db_share = BillShare(**share_kwargs)
        db.add(db_share)
        shares_out.append({"user_id": uid, "amount": float(share_amount)})

        # Tạo công nợ và thông báo (trừ người trả trước)
        if uid != bill_in.paid_by and share_amount > 0:
            create_debts(
                db=db,
                group_id=bill_in.group_id,
                source_type="INVOICE",
                debtor_id=uid,
                payee_id=bill_in.paid_by,
                amount=float(share_amount)
            )

            notif = Notification(
                user_id=uid,
                title=f"Hoá đơn mới: {bill_in.title}",
                message=f"Bạn cần thanh toán {share_amount:,}đ cho hoá đơn '{bill_in.title}'."
            )
            db.add(notif)

    db.commit()

    return {
        "id": db_bill.id,
        "group_id": db_bill.group_id,
        "title": db_bill.title,
        "bill_date": db_bill.bill_date,
        "total_amount": float(db_bill.total_amount),
        "paid_by": db_bill.paid_by,
        "split_type": db_bill.split_type,
        "note": db_bill.note,
        "image_url": db_bill.image_url,
        "shares": shares_out
    }
=======
from fastapi import HTTPException


def preview_bill(data):

    if data.split_type == "EQUAL":

        count = len(data.participants)

        if count == 0:
            raise HTTPException(
                status_code=400,
                detail="Participants cannot be empty"
            )

        amount_per_user = data.total_amount // count

        return [
            {
                "member_id": member,
                "amount": amount_per_user
            }
            for member in data.participants
        ]

    elif data.split_type == "CUSTOM":

        total_share = sum(
            share.amount
            for share in data.shares
        )

        if total_share != data.total_amount:
            raise HTTPException(
                status_code=400,
                detail="Total share amount does not match bill total amount"
            )

        return [
            {
                "member_id": share.member_id,
                "amount": share.amount
            }
            for share in data.shares
        ]

    elif data.split_type == "BY_ITEM":

        amounts = {}

        for item in data.items:

            item_total = item.unit_price * item.quantity

            split_amount = item_total // len(item.consumers)

            for consumer in item.consumers:
                amounts[consumer] = (
                    amounts.get(consumer, 0)
                    + split_amount
                )

        return [
            {
                "member_id": member_id,
                "amount": amount
            }
            for member_id, amount in amounts.items()
        ]

    raise HTTPException(
        status_code=400,
        detail="Invalid split type"
    )
>>>>>>> origin/feature/T3CDE80-minhthang
