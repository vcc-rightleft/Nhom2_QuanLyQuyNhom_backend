from datetime import date, datetime, time
import json
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.models.FundTransaction import FundTransaction, FundTransactionLog
from app.models.Calculate import get_group_fund_balance
from app.models.item import User
from app.schemas.transaction_history import (
    PaginatedTransactionHistoryResponse,
    UpdateFundTransactionRequest,
    CancelFundTransactionRequest,
    TransactionLogResponse,
)

router = APIRouter(
    prefix="/fund-transactions",
    tags=["Fund Transaction History & 24h Audit"],
)

EDIT_WINDOW_SECONDS = 24 * 3600  # 24 giờ


def _verify_group_member(db: Session, group_id: int, viewer_id: int) -> None:
    """
    Kiểm tra chỉ thành viên thuộc nhóm (group_id) mới có quyền xem lịch sử giao dịch.
    """
    if viewer_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ thành viên thuộc nhóm mới có quyền xem lịch sử giao dịch quỹ!",
        )

    try:
        group_users = db.query(User).filter(User.group_id == group_id).all()
    except Exception:
        group_users = []

    if group_users:
        member_ids = {u.id for u in group_users}
        if viewer_id not in member_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Người dùng ID={viewer_id} không phải là thành viên của nhóm quỹ #{group_id}!",
            )
    else:
        # Nếu bảng users chưa seed dữ liệu, mặc định nhóm 1 cho phép các thành viên mẫu (ID 1..10)
        if group_id == 1 and viewer_id not in range(1, 11):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Người dùng ID={viewer_id} không phải là thành viên của nhóm quỹ #{group_id}!",
            )


def _snapshot_tx(tx: FundTransaction) -> str:
    return json.dumps(
        {
            "type": tx.type,
            "amount": int(tx.amount or 0),
            "category": tx.category,
            "payer_id": tx.payer_id,
            "description": tx.description,
            "proof_image_url": tx.proof_image_url,
            "status": getattr(tx, "status", "ACTIVE") or "ACTIVE",
            "occurred_at": tx.occurred_at.isoformat() if tx.occurred_at else None,
        },
        ensure_ascii=False,
    )


def _check_within_24_hours(tx: FundTransaction) -> None:
    base_time = tx.created_at or tx.occurred_at
    if not base_time:
        return
    elapsed_seconds = (datetime.utcnow() - base_time).total_seconds()
    if elapsed_seconds > EDIT_WINDOW_SECONDS:
        hours_passed = round(elapsed_seconds / 3600, 1)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Chỉ cho phép Host sửa hoặc huỷ giao dịch trong vòng 24 giờ kể từ lúc tạo! "
                f"(Giao dịch này đã tạo cách đây {hours_passed} giờ)."
            ),
        )


@router.get(
    "/history/{group_id}",
    response_model=PaginatedTransactionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy lịch sử giao dịch quỹ (lọc theo loại, khoảng ngày, người, danh mục, phân trang; chỉ thành viên nhóm xem)",
)
def get_fund_transaction_history(
    group_id: int,
    viewer_id: int = Query(..., description="ID thành viên đang xem (bắt buộc là thành viên nhóm)"),
    tx_type: Optional[str] = Query(None, description="Lọc theo loại giao dịch: INCOME hoặc EXPENSE"),
    start_date: Optional[date] = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    payer_id: Optional[int] = Query(None, description="Lọc theo ID người nộp/chi"),
    category: Optional[str] = Query(None, description="Lọc theo danh mục (tìm kiếm khớp hoặc chứa từ khoá)"),
    status_filter: Optional[str] = Query(None, description="Lọc theo trạng thái: ACTIVE hoặc CANCELLED"),
    page: int = Query(1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng giao dịch mỗi trang"),
    db: Session = Depends(get_db),
):
    # 1. Kiểm tra quyền: Chỉ thành viên nhóm mới được xem
    _verify_group_member(db, group_id=group_id, viewer_id=viewer_id)

    # 2. Xây dựng truy vấn lọc
    query = db.query(FundTransaction).filter(FundTransaction.group_id == group_id)

    if tx_type and tx_type.strip():
        normalized_type = tx_type.strip().upper()
        if normalized_type not in ("INCOME", "EXPENSE"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Loại giao dịch (tx_type) chỉ nhận giá trị INCOME hoặc EXPENSE!",
            )
        query = query.filter(FundTransaction.type == normalized_type)

    if start_date:
        start_dt = datetime.combine(start_date, time.min)
        query = query.filter(FundTransaction.occurred_at >= start_dt)

    if end_date:
        end_dt = datetime.combine(end_date, time.max)
        query = query.filter(FundTransaction.occurred_at <= end_dt)

    if payer_id is not None:
        query = query.filter(FundTransaction.payer_id == payer_id)

    if category and category.strip():
        query = query.filter(FundTransaction.category.ilike(f"%{category.strip()}%"))

    if status_filter and status_filter.strip():
        query = query.filter(FundTransaction.status == status_filter.strip().upper())

    # 3. Tính tổng số bản ghi và phân trang
    total_records = query.count()
    total_pages = math.ceil(total_records / page_size) if total_records > 0 else 1
    offset = (page - 1) * page_size

    transactions = (
        query.order_by(
            FundTransaction.occurred_at.desc(),
            FundTransaction.transaction_id.desc(),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    fund_summary = get_group_fund_balance(db, group_id)

    return {
        "group_id": group_id,
        "viewer_id": viewer_id,
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "fund_summary": fund_summary,
        "items": transactions,
    }


@router.put(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    summary="Host sửa giao dịch quỹ trong vòng 24 giờ kèm lý do (ghi lại lịch sử sửa)",
)
def update_fund_transaction_within_24h(
    transaction_id: int,
    payload: UpdateFundTransactionRequest,
    db: Session = Depends(get_db),
):
    if payload.role.strip().upper() != "HOST":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Host mới có quyền sửa giao dịch quỹ!",
        )

    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập lý do sửa giao dịch!",
        )

    tx = (
        db.query(FundTransaction)
        .filter(FundTransaction.transaction_id == transaction_id)
        .first()
    )
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy giao dịch quỹ ID={transaction_id}!",
        )

    if getattr(tx, "status", "ACTIVE") == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giao dịch này đã bị huỷ, không thể chỉnh sửa!",
        )

    # Kiểm tra giới hạn 24 giờ
    _check_within_24_hours(tx)

    try:
        old_snapshot = _snapshot_tx(tx)

        if payload.type is not None:
            tx.type = payload.type
        if payload.amount is not None:
            tx.amount = payload.amount
        if payload.category is not None:
            tx.category = payload.category.strip()
        if payload.payer_id is not None:
            tx.payer_id = payload.payer_id
        if payload.description is not None:
            tx.description = payload.description
        if payload.proof_image_url is not None:
            tx.proof_image_url = payload.proof_image_url.strip()
        if payload.occurred_at is not None:
            tx.occurred_at = payload.occurred_at

        tx.updated_at = datetime.utcnow()
        db.flush()

        # Kiểm tra số dư sau khi sửa không được âm
        updated_fund = get_group_fund_balance(db, tx.group_id)
        if updated_fund["balance"] < 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Không thể cập nhật vì làm số dư quỹ bị âm "
                    f"({updated_fund['balance']:,} VND)!"
                ),
            )

        new_snapshot = _snapshot_tx(tx)

        audit_log = FundTransactionLog(
            transaction_id=tx.transaction_id,
            group_id=tx.group_id,
            action="UPDATE",
            changed_by=payload.host_id,
            reason=reason,
            old_data=old_snapshot,
            new_data=new_snapshot,
            changed_at=datetime.utcnow(),
        )
        db.add(audit_log)
        db.commit()
        db.refresh(tx)
        db.refresh(audit_log)

        return {
            "message": "Cập nhật giao dịch quỹ và ghi lịch sử sửa thành công!",
            "transaction": tx,
            "audit_log": audit_log,
            "fund_summary": updated_fund,
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi sửa giao dịch quỹ: {str(e)}",
        )


@router.post(
    "/{transaction_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Host huỷ giao dịch quỹ trong vòng 24 giờ kèm lý do (ghi lại lịch sử huỷ)",
)
@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    summary="Host huỷ giao dịch quỹ trong vòng 24 giờ kèm lý do",
)
def cancel_fund_transaction_within_24h(
    transaction_id: int,
    payload: CancelFundTransactionRequest,
    db: Session = Depends(get_db),
):
    if payload.role.strip().upper() != "HOST":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Host mới có quyền huỷ giao dịch quỹ!",
        )

    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập lý do huỷ giao dịch!",
        )

    tx = (
        db.query(FundTransaction)
        .filter(FundTransaction.transaction_id == transaction_id)
        .first()
    )
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy giao dịch quỹ ID={transaction_id}!",
        )

    if getattr(tx, "status", "ACTIVE") == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giao dịch này đã được huỷ trước đó!",
        )

    # Kiểm tra giới hạn 24 giờ
    _check_within_24_hours(tx)

    try:
        old_snapshot = _snapshot_tx(tx)
        tx.status = "CANCELLED"
        tx.updated_at = datetime.utcnow()
        db.flush()

        # Kiểm tra nếu huỷ khoản thu làm số dư quỹ bị âm thì chặn
        updated_fund = get_group_fund_balance(db, tx.group_id)
        if updated_fund["balance"] < 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Không thể huỷ khoản thu này vì sẽ làm số dư quỹ bị âm "
                    f"({updated_fund['balance']:,} VND)!"
                ),
            )

        new_snapshot = _snapshot_tx(tx)

        audit_log = FundTransactionLog(
            transaction_id=tx.transaction_id,
            group_id=tx.group_id,
            action="CANCEL",
            changed_by=payload.host_id,
            reason=reason,
            old_data=old_snapshot,
            new_data=new_snapshot,
            changed_at=datetime.utcnow(),
        )
        db.add(audit_log)
        db.commit()
        db.refresh(tx)
        db.refresh(audit_log)

        return {
            "message": "Huỷ giao dịch quỹ và ghi lịch sử huỷ thành công!",
            "transaction_id": tx.transaction_id,
            "status": tx.status,
            "audit_log": audit_log,
            "fund_summary": updated_fund,
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu khi huỷ giao dịch quỹ: {str(e)}",
        )


@router.get(
    "/{transaction_id}/logs",
    response_model=List[TransactionLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Xem lịch sử sửa/huỷ của một giao dịch quỹ",
)
def get_transaction_edit_logs(
    transaction_id: int,
    viewer_id: int = Query(1, description="ID thành viên đang xem"),
    db: Session = Depends(get_db),
):
    tx = (
        db.query(FundTransaction)
        .filter(FundTransaction.transaction_id == transaction_id)
        .first()
    )
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy giao dịch quỹ ID={transaction_id}!",
        )

    _verify_group_member(db, group_id=tx.group_id, viewer_id=viewer_id)

    return (
        db.query(FundTransactionLog)
        .filter(FundTransactionLog.transaction_id == transaction_id)
        .order_by(FundTransactionLog.log_id.desc())
        .all()
    )
