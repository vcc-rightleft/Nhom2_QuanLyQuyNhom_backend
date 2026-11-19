from decimal import Decimal
from typing import Dict, Iterable, List, Optional
from sqlalchemy.orm import Session
from app.models.debt_payment import (
    Debt,
    Payment,
    SourceTypeEnum,
    DebtStatusEnum,
    PaymentStatusEnum,
)


def create_debts(
    db: Session,
    group_id: int,
    source_type: str,
    debtor_id: int,
    payee_id: int,
    amount: float,
    source_id: Optional[int] = None,
    commit: bool = True,
):
    """
    Tạo khoản nợ mới từ hóa đơn (INVOICE) hoặc đợt thu quỹ (COLLECTION_PERIOD).
    """
    db_debt = Debt(
        group_id=group_id,
        source_type=source_type,
        source_id=source_id,
        debtor_id=debtor_id,
        payee_id=payee_id,
        amount=amount,
        paid_amount=0.00,
        status=DebtStatusEnum.UNPAID,
    )
    db.add(db_debt)
    if commit:
        db.commit()
        db.refresh(db_debt)
    else:
        db.flush()
    return db_debt


def cancel_debts(db: Session, debt_id: int, commit: bool = True):
    """
    Hủy khoản nợ khi hóa đơn hoặc giao dịch gốc bị hủy.
    """
    db_debt = db.query(Debt).filter(Debt.id == debt_id).first()
    if db_debt:
        db.delete(db_debt)
        if commit:
            db.commit()
        else:
            db.flush()
        return True
    return False


def get_debts_by_bill(
    db: Session,
    bill_id: int,
    debt_ids: Optional[Iterable[int]] = None,
) -> List[Debt]:
    """
    Lấy danh sách toàn bộ khoản nợ thuộc một hoá đơn theo source_id hoặc danh sách debt_id từ bill_shares.
    """
    found: Dict[int, Debt] = {}

    by_source = (
        db.query(Debt)
        .filter(
            Debt.source_type == SourceTypeEnum.INVOICE,
            Debt.source_id == bill_id,
        )
        .all()
    )
    for d in by_source:
        found[d.id] = d

    valid_ids = [int(did) for did in (debt_ids or []) if did is not None]
    if valid_ids:
        by_ids = db.query(Debt).filter(Debt.id.in_(valid_ids)).all()
        for d in by_ids:
            found[d.id] = d

    return list(found.values())


def has_any_debt_payment(
    db: Session,
    bill_id: int,
    debt_ids: Optional[Iterable[int]] = None,
) -> bool:
    """
    Kiểm tra xem đã có ai thanh toán (hoặc gửi phiếu thanh toán PENDING/CONFIRMED)
    cho bất kỳ khoản nợ nào của hoá đơn hay chưa.
    """
    debts = get_debts_by_bill(db, bill_id=bill_id, debt_ids=debt_ids)
    if not debts:
        return False

    for debt in debts:
        paid_val = Decimal(str(debt.paid_amount or 0))
        if paid_val > Decimal("0") or debt.status != DebtStatusEnum.UNPAID:
            return True

    all_debt_ids = [d.id for d in debts]
    active_payment = (
        db.query(Payment)
        .filter(
            Payment.debt_id.in_(all_debt_ids),
            Payment.status.in_([PaymentStatusEnum.PENDING, PaymentStatusEnum.CONFIRMED]),
        )
        .first()
    )
    return active_payment is not None


def cancel_bill_debts(
    db: Session,
    bill_id: int,
    debt_ids: Optional[Iterable[int]] = None,
    commit: bool = True,
) -> int:
    """
    Huỷ toàn bộ khoản nợ gắn với hoá đơn (chỉ gọi khi đã kiểm tra chưa ai thanh toán).
    Trả về số lượng khoản nợ đã huỷ.
    """
    debts = get_debts_by_bill(db, bill_id=bill_id, debt_ids=debt_ids)
    cancelled_count = 0
    for debt in debts:
        if cancel_debts(db, debt_id=debt.id, commit=False):
            cancelled_count += 1
    if commit:
        db.commit()
    else:
        db.flush()
    return cancelled_count


def replace_bill_debts(
    db: Session,
    group_id: int,
    bill_id: int,
    payee_id: int,
    shares: List[Dict[str, int]],
    old_debt_ids: Optional[Iterable[int]] = None,
    commit: bool = True,
) -> Dict[int, int]:
    """
    Cập nhật lại toàn bộ công nợ của hoá đơn sau khi sửa hoá đơn:
    1. Huỷ các khoản nợ cũ của hoá đơn.
    2. Tạo mới các khoản nợ cho từng thành viên có member_id != payee_id và amount > 0.
    Trả về mapping {member_id: debt_id}.
    """
    cancel_bill_debts(db, bill_id=bill_id, debt_ids=old_debt_ids, commit=False)

    member_to_debt_id: Dict[int, int] = {}
    for share in shares:
        member_id = int(share["member_id"])
        amount = Decimal(str(share["amount"]))
        if member_id == int(payee_id) or amount <= Decimal("0"):
            continue
        new_debt = create_debts(
            db=db,
            group_id=group_id,
            source_type=SourceTypeEnum.INVOICE,
            debtor_id=member_id,
            payee_id=payee_id,
            amount=amount,
            source_id=bill_id,
            commit=False,
        )
        member_to_debt_id[member_id] = new_debt.id

    if commit:
        db.commit()
    else:
        db.flush()
    return member_to_debt_id


def get_debts_owed_by_me(db: Session, user_id: int, group_id: int = None):
    """
    API: Lấy danh sách các khoản tôi nợ người khác.
    Hỗ trợ lọc theo từng nhóm cụ thể (group_id) hoặc lấy tổng tất cả các nhóm (group_id = None).
    """
    query = db.query(Debt).filter(
        Debt.debtor_id == user_id,
        Debt.status != DebtStatusEnum.PAID,
    )
    if group_id is not None:
        query = query.filter(Debt.group_id == group_id)
    return query.all()


def get_debts_owed_to_me(db: Session, user_id: int, group_id: int = None):
    """
    API: Lấy danh sách các khoản người khác nợ tôi.
    Hỗ trợ lọc theo từng nhóm cụ thể (group_id) hoặc lấy tổng tất cả các nhóm (group_id = None).
    """
    query = db.query(Debt).filter(
        Debt.payee_id == user_id,
        Debt.status != DebtStatusEnum.PAID,
    )
    if group_id is not None:
        query = query.filter(Debt.group_id == group_id)
    return query.all()