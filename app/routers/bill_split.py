from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.models.Bill import Bill, SplitTypeEnum, FeeSplitModeEnum
from app.models.Bill_item import BillItem
from app.models.Bill_share import BillShare
from app.models.debt_payment import Debt, SourceTypeEnum, DebtStatusEnum
from app.schemas.bill_split import (
    ItemizedSplitRequest,
    CustomSplitRequest,
    BillSplitResponse,
)

router = APIRouter(prefix="/bills", tags=["Bill Splitting (Itemized & Custom)"])

CENT = Decimal("0.01")


def _split_amount_equally(total: Decimal, user_ids: List[int]) -> Dict[int, Decimal]:
    """
    Chia đều một khoản tiền (total) cho danh sách user_ids.
    Phần dư làm tròn (0.01) được phân bổ lần lượt cho các thành viên đầu tiên
    để đảm bảo tổng các phần bằng chính xác 100% total.
    """
    count = len(user_ids)
    if count == 0:
        return {}

    total = total.quantize(CENT, rounding=ROUND_HALF_UP)
    base_share = (total / Decimal(count)).quantize(CENT, rounding=ROUND_DOWN)
    remainder = total - (base_share * Decimal(count))
    steps = int((remainder / CENT).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    allocations: Dict[int, Decimal] = {}
    for idx, uid in enumerate(user_ids):
        extra = CENT if idx < steps else Decimal("0.00")
        allocations[uid] = base_share + extra
    return allocations


def _split_fee_proportionally(
    total_fee: Decimal, member_item_totals: Dict[int, Decimal], items_subtotal: Decimal
) -> Dict[int, Decimal]:
    """
    Chia phí ship/phục vụ theo tỉ lệ tiền món của từng thành viên:
    fee_i = total_fee * (items_amount_i / items_subtotal).
    Bù phần dư làm tròn để tổng phí phân bổ bằng chính xác total_fee.
    """
    user_ids = list(member_item_totals.keys())
    if not user_ids:
        return {}

    total_fee = total_fee.quantize(CENT, rounding=ROUND_HALF_UP)
    if total_fee == Decimal("0.00") or items_subtotal <= Decimal("0.00"):
        return {uid: Decimal("0.00") for uid in user_ids}

    fee_allocations: Dict[int, Decimal] = {}
    for uid in user_ids:
        raw_fee = (total_fee * member_item_totals[uid]) / items_subtotal
        fee_allocations[uid] = raw_fee.quantize(CENT, rounding=ROUND_DOWN)

    allocated_sum = sum(fee_allocations.values(), Decimal("0.00"))
    remainder = total_fee - allocated_sum
    steps = int((remainder / CENT).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    # Ưu tiên cộng phần dư 0.01 cho người có tiền món lớn hơn
    sorted_uids = sorted(user_ids, key=lambda u: member_item_totals[u], reverse=True)
    for idx in range(steps):
        target_uid = sorted_uids[idx % len(sorted_uids)]
        fee_allocations[target_uid] += CENT

    return fee_allocations


def calculate_itemized_split(payload: ItemizedSplitRequest) -> dict:
    """
    Tính toán chi tiết chia tiền theo món ăn (Itemized Split):
    - Mỗi món gán cho 1 hoặc nhiều người (món dùng chung chia đều trong số người đó).
    - Phí ship/phục vụ chia đều (EQUAL) hoặc theo tỉ lệ tiền món (PROPORTIONAL).
    """
    member_item_totals: Dict[int, Decimal] = {}
    processed_items = []
    items_subtotal = Decimal("0.00")

    for item in payload.items:
        unique_users = list(dict.fromkeys(item.user_ids))
        if not unique_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Món '{item.item_name}' phải được gán cho ít nhất 1 thành viên!",
            )

        line_total = (Decimal(item.quantity) * item.unit_price).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        items_subtotal += line_total

        per_item_shares = _split_amount_equally(line_total, unique_users)
        for uid, share_val in per_item_shares.items():
            member_item_totals[uid] = member_item_totals.get(uid, Decimal("0.00")) + share_val

        processed_items.append(
            {
                "item_name": item.item_name.strip(),
                "quantity": item.quantity,
                "unit_price": item.unit_price.quantize(CENT, rounding=ROUND_HALF_UP),
                "total_price": line_total,
                "participant_ids": unique_users,
            }
        )

    service_ship_fee = (payload.service_ship_fee or Decimal("0.00")).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    calculated_total = items_subtotal + service_ship_fee

    if payload.total_amount is not None:
        expected_total = payload.total_amount.quantize(CENT, rounding=ROUND_HALF_UP)
        if expected_total != calculated_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Tổng hoá đơn truyền vào ({expected_total}) không khớp với "
                    f"tổng tiền các món + phí ship/phục vụ ({calculated_total})!"
                ),
            )

    participant_ids = list(member_item_totals.keys())
    if payload.fee_split_mode == FeeSplitModeEnum.PROPORTIONAL.value:
        fee_shares = _split_fee_proportionally(
            service_ship_fee, member_item_totals, items_subtotal
        )
    else:
        fee_shares = _split_amount_equally(service_ship_fee, participant_ids)

    member_shares = []
    for uid in participant_ids:
        item_amt = member_item_totals[uid].quantize(CENT, rounding=ROUND_HALF_UP)
        fee_amt = fee_shares.get(uid, Decimal("0.00")).quantize(CENT, rounding=ROUND_HALF_UP)
        total_share = item_amt + fee_amt
        member_shares.append(
            {
                "user_id": uid,
                "items_amount": item_amt,
                "fee_amount": fee_amt,
                "total_share_amount": total_share,
            }
        )

    return {
        "items_subtotal": items_subtotal,
        "service_ship_fee": service_ship_fee,
        "total_amount": calculated_total,
        "processed_items": processed_items,
        "member_shares": member_shares,
    }


def calculate_custom_split(payload: CustomSplitRequest) -> dict:
    """
    Tính toán và kiểm tra chia tiền tuỳ chỉnh (Custom Split):
    - Nhập số tiền từng người, tổng các phần phải khớp chính xác với tổng hoá đơn.
    """
    total_amount = payload.total_amount.quantize(CENT, rounding=ROUND_HALF_UP)

    aggregated_shares: Dict[int, Decimal] = {}
    for s in payload.shares:
        amt = s.amount.quantize(CENT, rounding=ROUND_HALF_UP)
        aggregated_shares[s.user_id] = aggregated_shares.get(s.user_id, Decimal("0.00")) + amt

    sum_shares = sum(aggregated_shares.values(), Decimal("0.00")).quantize(
        CENT, rounding=ROUND_HALF_UP
    )

    if sum_shares != total_amount:
        diff = sum_shares - total_amount
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tổng số tiền của các thành viên ({sum_shares}) không khớp với "
                f"tổng hoá đơn ({total_amount})! Chênh lệch: {diff}."
            ),
        )

    member_shares = [
        {
            "user_id": uid,
            "items_amount": amt,
            "fee_amount": Decimal("0.00"),
            "total_share_amount": amt,
        }
        for uid, amt in aggregated_shares.items()
    ]

    return {
        "items_subtotal": total_amount,
        "service_ship_fee": Decimal("0.00"),
        "total_amount": total_amount,
        "member_shares": member_shares,
    }


@router.post(
    "/split-by-items",
    response_model=BillSplitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Chia hoá đơn theo món ăn (món dùng chung chia đều, phí ship/phục vụ chia đều hoặc theo tỉ lệ)",
)
def api_split_bill_by_items(
    payload: ItemizedSplitRequest, db: Session = Depends(get_db)
):
    calc = calculate_itemized_split(payload)

    try:
        new_bill = Bill(
            group_id=payload.group_id,
            title=payload.title.strip(),
            payer_id=payload.payer_id,
            split_type=SplitTypeEnum.ITEMIZED.value,
            fee_split_mode=payload.fee_split_mode,
            items_subtotal=calc["items_subtotal"],
            service_ship_fee=calc["service_ship_fee"],
            total_amount=calc["total_amount"],
            created_by=payload.created_by,
        )
        db.add(new_bill)
        db.flush()

        for item_data in calc["processed_items"]:
            db_item = BillItem(
                bill_id=new_bill.id,
                item_name=item_data["item_name"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                total_price=item_data["total_price"],
                participant_ids=",".join(str(uid) for uid in item_data["participant_ids"]),
            )
            db.add(db_item)

        share_results = []
        debts_created = 0

        for share in calc["member_shares"]:
            debt_id = None
            # Tạo công nợ (INVOICE) như hoá đơn chia đều cho các thành viên khác người trả hoá đơn
            if share["total_share_amount"] > Decimal("0.00") and share["user_id"] != payload.payer_id:
                db_debt = Debt(
                    group_id=payload.group_id,
                    source_type=SourceTypeEnum.INVOICE,
                    debtor_id=share["user_id"],
                    payee_id=payload.payer_id,
                    amount=share["total_share_amount"],
                    paid_amount=Decimal("0.00"),
                    status=DebtStatusEnum.UNPAID,
                )
                db.add(db_debt)
                db.flush()
                debt_id = db_debt.id
                debts_created += 1

            db_share = BillShare(
                bill_id=new_bill.id,
                user_id=share["user_id"],
                items_amount=share["items_amount"],
                fee_amount=share["fee_amount"],
                total_share_amount=share["total_share_amount"],
                debt_id=debt_id,
            )
            db.add(db_share)

            share_results.append(
                {
                    **share,
                    "debt_id": debt_id,
                }
            )

        db.commit()
        db.refresh(new_bill)

        return {
            "message": "Chia hoá đơn theo món ăn và khởi tạo công nợ thành công!",
            "bill_id": new_bill.id,
            "group_id": new_bill.group_id,
            "title": new_bill.title,
            "payer_id": new_bill.payer_id,
            "split_type": new_bill.split_type,
            "fee_split_mode": new_bill.fee_split_mode,
            "items_subtotal": calc["items_subtotal"],
            "service_ship_fee": calc["service_ship_fee"],
            "total_amount": calc["total_amount"],
            "total_debts_created": debts_created,
            "shares": share_results,
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi lưu hoá đơn chia theo món: {str(e)}",
        )


@router.post(
    "/split-custom",
    response_model=BillSplitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Chia hoá đơn tuỳ chỉnh (nhập số tiền từng người, tổng phải khớp tổng hoá đơn)",
)
def api_split_bill_custom(
    payload: CustomSplitRequest, db: Session = Depends(get_db)
):
    calc = calculate_custom_split(payload)

    try:
        new_bill = Bill(
            group_id=payload.group_id,
            title=payload.title.strip(),
            payer_id=payload.payer_id,
            split_type=SplitTypeEnum.CUSTOM.value,
            fee_split_mode=None,
            items_subtotal=calc["items_subtotal"],
            service_ship_fee=Decimal("0.00"),
            total_amount=calc["total_amount"],
            created_by=payload.created_by,
        )
        db.add(new_bill)
        db.flush()

        share_results = []
        debts_created = 0

        for share in calc["member_shares"]:
            debt_id = None
            # Tạo công nợ (INVOICE) như hoá đơn chia đều cho các thành viên có số tiền > 0 khác người ứng tiền
            if share["total_share_amount"] > Decimal("0.00") and share["user_id"] != payload.payer_id:
                db_debt = Debt(
                    group_id=payload.group_id,
                    source_type=SourceTypeEnum.INVOICE,
                    debtor_id=share["user_id"],
                    payee_id=payload.payer_id,
                    amount=share["total_share_amount"],
                    paid_amount=Decimal("0.00"),
                    status=DebtStatusEnum.UNPAID,
                )
                db.add(db_debt)
                db.flush()
                debt_id = db_debt.id
                debts_created += 1

            db_share = BillShare(
                bill_id=new_bill.id,
                user_id=share["user_id"],
                items_amount=share["items_amount"],
                fee_amount=Decimal("0.00"),
                total_share_amount=share["total_share_amount"],
                debt_id=debt_id,
            )
            db.add(db_share)

            share_results.append(
                {
                    **share,
                    "debt_id": debt_id,
                }
            )

        db.commit()
        db.refresh(new_bill)

        return {
            "message": "Chia hoá đơn tuỳ chỉnh và khởi tạo công nợ thành công!",
            "bill_id": new_bill.id,
            "group_id": new_bill.group_id,
            "title": new_bill.title,
            "payer_id": new_bill.payer_id,
            "split_type": new_bill.split_type,
            "fee_split_mode": None,
            "items_subtotal": calc["items_subtotal"],
            "service_ship_fee": Decimal("0.00"),
            "total_amount": calc["total_amount"],
            "total_debts_created": debts_created,
            "shares": share_results,
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi lưu hoá đơn chia tuỳ chỉnh: {str(e)}",
        )


@router.get("/{bill_id}", summary="Xem chi tiết hoá đơn và phân bổ công nợ")
def api_get_bill_detail(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hoá đơn!",
        )
    return {
        "bill_id": bill.id,
        "group_id": bill.group_id,
        "title": bill.title,
        "payer_id": bill.payer_id,
        "split_type": bill.split_type,
        "fee_split_mode": bill.fee_split_mode,
        "items_subtotal": bill.items_subtotal,
        "service_ship_fee": bill.service_ship_fee,
        "total_amount": bill.total_amount,
        "created_by": bill.created_by,
        "created_at": bill.created_at,
        "items": bill.items,
        "shares": bill.shares,
    }


