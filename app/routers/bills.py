from datetime import date, datetime, time
import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import debt as crud_debt
from app.db.session import get_db
from app.models.Bill import Bill
from app.models.Bill_item import BillItem
from app.models.Bill_share import BillShare
from app.models.debt_payment import Debt
from app.models.user import User
from app.schemas.bill import (
    BillCancelResponse,
    BillDetailResponse,
    BillItemDetail,
    BillItemInput,
    BillListItem,
    BillListResponse,
    BillShareDetail,
    BillUpdateRequest,
)

router = APIRouter(
    prefix="/bills",
    tags=["Bills Management (Hoá đơn)"],
)

VALID_SPLIT_TYPES = {"EQUAL", "ITEMIZED", "CUSTOM"}


def _parse_consumer_ids(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    text_val = raw.strip()
    if not text_val:
        return []
    if text_val.startswith("["):
        try:
            parsed = json.loads(text_val)
            return [int(x) for x in parsed if str(x).strip().isdigit()]
        except Exception:
            pass
    result: List[int] = []
    for token in text_val.split(","):
        token = token.strip()
        if token.isdigit():
            result.append(int(token))
    return result


def _serialize_consumer_ids(user_ids: List[int]) -> Optional[str]:
    unique_ids = list(dict.fromkeys(int(uid) for uid in user_ids if int(uid) > 0))
    if not unique_ids:
        return None
    return ",".join(str(uid) for uid in unique_ids)


def _split_equally_vnd(total: int, user_ids: List[int]) -> Dict[int, int]:
    unique_users = list(dict.fromkeys(int(uid) for uid in user_ids if int(uid) > 0))
    if not unique_users:
        return {}
    base = total // len(unique_users)
    remainder = total % len(unique_users)
    allocations: Dict[int, int] = {}
    for idx, uid in enumerate(unique_users):
        allocations[uid] = base + (1 if idx < remainder else 0)
    return allocations


def _calculate_shares_from_items(items: List[BillItemInput]) -> tuple[int, List[Dict[str, int]]]:
    member_totals: Dict[int, int] = {}
    total_amount = 0
    for item in items:
        line_total = int(item.unit_price) * int(item.quantity)
        total_amount += line_total
        unique_consumers = list(dict.fromkeys(int(uid) for uid in item.consumer_user_ids if int(uid) > 0))
        if not unique_consumers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Món '{item.name}' phải có ít nhất 1 thành viên sử dụng (consumer_user_ids).",
            )
        per_item = _split_equally_vnd(line_total, unique_consumers)
        for uid, amount in per_item.items():
            member_totals[uid] = member_totals.get(uid, 0) + amount

    shares = [{"member_id": uid, "amount": amt} for uid, amt in member_totals.items()]
    return total_amount, shares


def _load_user_names(db: Session, user_ids: List[int]) -> Dict[int, str]:
    valid_ids = list({int(uid) for uid in user_ids if uid is not None})
    if not valid_ids:
        return {}
    try:
        users = db.query(User).filter(User.id.in_(valid_ids)).all()
        return {u.id: u.full_name for u in users}
    except Exception:
        return {}


def _build_bill_detail(db: Session, bill: Bill) -> BillDetailResponse:
    bill_items = (
        db.query(BillItem)
        .filter(BillItem.bill_id == bill.id)
        .order_by(BillItem.id.asc())
        .all()
    )
    bill_shares = (
        db.query(BillShare)
        .filter(BillShare.bill_id == bill.id)
        .order_by(BillShare.id.asc())
        .all()
    )

    share_debt_ids = [s.debt_id for s in bill_shares if s.debt_id is not None]
    debts = crud_debt.get_debts_by_bill(db, bill_id=bill.id, debt_ids=share_debt_ids)
    debt_by_id: Dict[int, Debt] = {d.id: d for d in debts}
    debt_by_debtor: Dict[int, Debt] = {d.debtor_id: d for d in debts}

    bill_status = (getattr(bill, "status", None) or "ACTIVE").upper()
    can_edit_or_cancel = (
        bill_status != "CANCELLED"
        and not crud_debt.has_any_debt_payment(db, bill_id=bill.id, debt_ids=share_debt_ids)
    )

    user_ids = [bill.paid_by] + [s.member_id for s in bill_shares]
    user_names = _load_user_names(db, user_ids)

    item_details = [
        BillItemDetail(
            id=item.id,
            bill_id=item.bill_id,
            name=item.name,
            unit_price=int(item.unit_price),
            quantity=int(item.quantity),
            line_total=int(item.unit_price) * int(item.quantity),
            consumer_user_ids=_parse_consumer_ids(item.consumer_user_ids),
        )
        for item in bill_items
    ]

    share_details: List[BillShareDetail] = []
    for share in bill_shares:
        matched_debt = (
            debt_by_id.get(share.debt_id)
            if share.debt_id is not None
            else debt_by_debtor.get(share.member_id)
        )
        debt_status_str = None
        paid_amount_int = 0
        resolved_debt_id = share.debt_id
        if matched_debt is not None:
            resolved_debt_id = matched_debt.id
            debt_status_str = (
                matched_debt.status.value
                if hasattr(matched_debt.status, "value")
                else str(matched_debt.status)
            )
            paid_amount_int = int(matched_debt.paid_amount or 0)
        elif share.member_id == bill.paid_by:
            debt_status_str = "PAYER"

        share_details.append(
            BillShareDetail(
                id=share.id,
                bill_id=share.bill_id,
                member_id=share.member_id,
                member_name=user_names.get(share.member_id),
                amount=int(share.amount),
                debt_id=resolved_debt_id,
                debt_status=debt_status_str,
                paid_amount=paid_amount_int,
            )
        )

    return BillDetailResponse(
        id=bill.id,
        group_id=bill.group_id,
        title=bill.title,
        bill_date=bill.bill_date,
        total_amount=int(bill.total_amount),
        paid_by=bill.paid_by,
        paid_by_name=user_names.get(bill.paid_by),
        split_type=bill.split_type,
        status=bill_status,
        note=bill.note,
        image_url=bill.image_url,
        can_edit_or_cancel=can_edit_or_cancel,
        items=item_details,
        shares=share_details,
    )


@router.get(
    "/groups/{group_id}",
    response_model=BillListResponse,
    status_code=status.HTTP_200_OK,
    summary="Danh sách hoá đơn của nhóm (lọc theo khoảng ngày, người trả, trạng thái)",
)
def list_group_bills(
    group_id: int,
    start_date: Optional[date] = Query(None, description="Lọc từ ngày (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Lọc đến ngày (YYYY-MM-DD)"),
    paid_by: Optional[int] = Query(None, description="Lọc theo ID người trả tiền"),
    bill_status: Optional[str] = Query(
        None,
        alias="status",
        description="Lọc theo trạng thái hoá đơn: ACTIVE hoặc CANCELLED",
    ),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date không được lớn hơn end_date.",
        )

    query = db.query(Bill).filter(Bill.group_id == group_id)

    if start_date is not None:
        query = query.filter(Bill.bill_date >= datetime.combine(start_date, time.min))
    if end_date is not None:
        query = query.filter(Bill.bill_date <= datetime.combine(end_date, time.max))
    if paid_by is not None:
        query = query.filter(Bill.paid_by == paid_by)
    if bill_status is not None:
        normalized_status = bill_status.strip().upper()
        if normalized_status not in {"ACTIVE", "CANCELLED"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trạng thái status chỉ nhận ACTIVE hoặc CANCELLED.",
            )
        query = query.filter(Bill.status == normalized_status)

    total = query.count()
    bills = (
        query.order_by(Bill.bill_date.desc(), Bill.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    user_names = _load_user_names(db, [b.paid_by for b in bills])

    result_items: List[BillListItem] = []
    for bill in bills:
        item_count = db.query(BillItem).filter(BillItem.bill_id == bill.id).count()
        shares = db.query(BillShare).filter(BillShare.bill_id == bill.id).all()
        share_debt_ids = [s.debt_id for s in shares if s.debt_id is not None]
        status_str = (getattr(bill, "status", None) or "ACTIVE").upper()
        can_modify = (
            status_str != "CANCELLED"
            and not crud_debt.has_any_debt_payment(db, bill_id=bill.id, debt_ids=share_debt_ids)
        )
        result_items.append(
            BillListItem(
                id=bill.id,
                group_id=bill.group_id,
                title=bill.title,
                bill_date=bill.bill_date,
                total_amount=int(bill.total_amount),
                paid_by=bill.paid_by,
                paid_by_name=user_names.get(bill.paid_by),
                split_type=bill.split_type,
                status=status_str,
                note=bill.note,
                image_url=bill.image_url,
                item_count=item_count,
                share_count=len(shares),
                can_edit_or_cancel=can_modify,
            )
        )

    return BillListResponse(
        group_id=group_id,
        total=total,
        page=page,
        page_size=page_size,
        items=result_items,
    )


@router.get(
    "/{bill_id}",
    response_model=BillDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết hoá đơn (kèm danh sách từng món và phần của từng người)",
)
def get_bill_detail(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy hoá đơn ID={bill_id}.",
        )
    return _build_bill_detail(db, bill)


@router.put(
    "/{bill_id}",
    response_model=BillDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Sửa hoá đơn (chỉ cho phép khi chưa ai thanh toán nợ; tự động cập nhật lại công nợ)",
)
def update_bill(
    bill_id: int,
    payload: BillUpdateRequest,
    db: Session = Depends(get_db),
):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy hoá đơn ID={bill_id}.",
        )

    if (getattr(bill, "status", None) or "ACTIVE").upper() == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hoá đơn đã bị huỷ, không thể chỉnh sửa.",
        )

    existing_shares = db.query(BillShare).filter(BillShare.bill_id == bill.id).all()
    old_debt_ids = [s.debt_id for s in existing_shares if s.debt_id is not None]

    # Ràng buộc cốt lõi: chỉ sửa khi chưa ai thanh toán khoản nợ của hoá đơn đó
    if crud_debt.has_any_debt_payment(db, bill_id=bill.id, debt_ids=old_debt_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể sửa hoá đơn vì đã có thành viên thanh toán khoản nợ của hoá đơn này.",
        )

    effective_split_type = (payload.split_type or bill.split_type or "EQUAL").strip().upper()
    if effective_split_type not in VALID_SPLIT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="split_type chỉ chấp nhận EQUAL, ITEMIZED hoặc CUSTOM.",
        )

    effective_paid_by = payload.paid_by if payload.paid_by is not None else bill.paid_by
    effective_total = (
        int(payload.total_amount)
        if payload.total_amount is not None
        else int(bill.total_amount)
    )

    new_shares_data: Optional[List[Dict[str, int]]] = None

    if payload.items is not None:
        if effective_split_type == "ITEMIZED" and payload.shares is None:
            computed_total, computed_shares = _calculate_shares_from_items(payload.items)
            if payload.total_amount is not None and int(payload.total_amount) != computed_total:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Tổng tiền hoá đơn ({payload.total_amount}) không khớp tổng tiền các món ({computed_total})."
                    ),
                )
            effective_total = computed_total
            new_shares_data = computed_shares

    if payload.shares is not None:
        seen_members = set()
        parsed_shares: List[Dict[str, int]] = []
        shares_sum = 0
        for s in payload.shares:
            if s.member_id in seen_members:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Thành viên ID={s.member_id} bị trùng lặp trong danh sách shares.",
                )
            seen_members.add(s.member_id)
            shares_sum += int(s.amount)
            parsed_shares.append({"member_id": int(s.member_id), "amount": int(s.amount)})

        if not parsed_shares:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh sách shares không được rỗng.",
            )
        if shares_sum != effective_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tổng phần chia ({shares_sum}) phải bằng tổng tiền hoá đơn ({effective_total}).",
            )
        new_shares_data = parsed_shares
    elif effective_split_type == "EQUAL" and (
        payload.participant_ids is not None or payload.total_amount is not None
    ):
        target_users = (
            payload.participant_ids
            if payload.participant_ids is not None
            else [s.member_id for s in existing_shares]
        )
        if not target_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cần cung cấp danh sách thành viên (participant_ids) để chia đều.",
            )
        allocations = _split_equally_vnd(effective_total, target_users)
        new_shares_data = [
            {"member_id": uid, "amount": amt} for uid, amt in allocations.items()
        ]
    elif new_shares_data is None:
        new_shares_data = [
            {"member_id": s.member_id, "amount": int(s.amount)} for s in existing_shares
        ]
        if payload.total_amount is not None and new_shares_data:
            existing_sum = sum(s["amount"] for s in new_shares_data)
            if existing_sum != effective_total:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Tổng tiền hoá đơn mới ({effective_total}) không khớp tổng phần chia hiện tại ({existing_sum}). "
                        "Vui lòng truyền kèm shares hoặc items tương ứng."
                    ),
                )

    try:
        if payload.title is not None:
            bill.title = payload.title.strip()
        if payload.bill_date is not None:
            bill.bill_date = payload.bill_date
        bill.total_amount = effective_total
        bill.paid_by = effective_paid_by
        bill.split_type = effective_split_type
        if payload.note is not None:
            bill.note = payload.note
        if payload.image_url is not None:
            bill.image_url = payload.image_url

        if payload.items is not None:
            db.query(BillItem).filter(BillItem.bill_id == bill.id).delete(
                synchronize_session=False
            )
            for item_in in payload.items:
                db.add(
                    BillItem(
                        bill_id=bill.id,
                        name=item_in.name.strip(),
                        unit_price=int(item_in.unit_price),
                        quantity=int(item_in.quantity),
                        consumer_user_ids=_serialize_consumer_ids(item_in.consumer_user_ids),
                    )
                )

        # Cập nhật lại công nợ qua module Công nợ
        member_to_debt_id = crud_debt.replace_bill_debts(
            db=db,
            group_id=bill.group_id,
            bill_id=bill.id,
            payee_id=effective_paid_by,
            shares=new_shares_data,
            old_debt_ids=old_debt_ids,
            commit=False,
        )

        db.query(BillShare).filter(BillShare.bill_id == bill.id).delete(
            synchronize_session=False
        )
        for s_data in new_shares_data:
            member_id = s_data["member_id"]
            db.add(
                BillShare(
                    bill_id=bill.id,
                    member_id=member_id,
                    amount=s_data["amount"],
                    debt_id=member_to_debt_id.get(member_id),
                )
            )

        db.commit()
        db.refresh(bill)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi cập nhật hoá đơn: {str(exc)}",
        )

    return _build_bill_detail(db, bill)


@router.delete(
    "/{bill_id}",
    response_model=BillCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Huỷ hoá đơn (chỉ cho phép khi chưa ai thanh toán nợ; tự động huỷ công nợ)",
)
def cancel_bill(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy hoá đơn ID={bill_id}.",
        )

    if (getattr(bill, "status", None) or "ACTIVE").upper() == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hoá đơn này đã được huỷ trước đó.",
        )

    shares = db.query(BillShare).filter(BillShare.bill_id == bill.id).all()
    debt_ids = [s.debt_id for s in shares if s.debt_id is not None]

    # Ràng buộc cốt lõi: chỉ huỷ khi chưa ai thanh toán khoản nợ của hoá đơn đó
    if crud_debt.has_any_debt_payment(db, bill_id=bill.id, debt_ids=debt_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể huỷ hoá đơn vì đã có thành viên thanh toán khoản nợ của hoá đơn này.",
        )

    try:
        cancelled_count = crud_debt.cancel_bill_debts(
            db=db,
            bill_id=bill.id,
            debt_ids=debt_ids,
            commit=False,
        )

        bill.status = "CANCELLED"
        for share in shares:
            share.debt_id = None

        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi huỷ hoá đơn: {str(exc)}",
        )

    return BillCancelResponse(
        message=f"Đã huỷ hoá đơn #{bill_id} và huỷ {cancelled_count} khoản công nợ liên quan.",
        bill_id=bill.id,
        status="CANCELLED",
        cancelled_debts_count=cancelled_count,
    )