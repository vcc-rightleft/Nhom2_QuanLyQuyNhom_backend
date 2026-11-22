import calendar
import csv
import io
import json
import math
from datetime import date, datetime, time
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User, SystemRole
from app.models.Calculate import get_group_fund_balance
from app.models.FundTransaction import FundTransaction, FundTransactionLog
from app.models.group_member import GroupMember
from app.schemas.transaction_history import (
    CancelFundTransactionRequest,
    PaginatedTransactionHistoryResponse,
    TransactionLogResponse,
    UpdateFundTransactionRequest,
)

router = APIRouter(
    prefix="/fund-transactions",
    tags=["Fund Transaction History & 24h Audit"],
)

EDIT_WINDOW_SECONDS = 24 * 3600  # 24 giờ


def _verify_group_member(db: Session, group_id: int, viewer_id: int) -> None:
    """Kiểm tra chỉ thành viên thuộc nhóm (group_id) mới có quyền xem lịch sử giao dịch."""
    if viewer_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ thành viên thuộc nhóm mới có quyền xem lịch sử giao dịch quỹ!",
        )

    try:
        memberships = (
            db.query(GroupMember)
            .filter(GroupMember.group_id == group_id, GroupMember.status == "ACTIVE")
            .all()
        )
    except Exception:
        memberships = []

    if not memberships or viewer_id not in {m.user_id for m in memberships}:
        raise HTTPException(status_code=403, detail="Bạn không phải thành viên đang hoạt động của nhóm")


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


def _resolve_period_bounds(
    month: Optional[str], start_date: Optional[date], end_date: Optional[date]
) -> Tuple[Optional[datetime], Optional[datetime], str]:
    """Chuyển tham số month (YYYY-MM) hoặc khoảng ngày thành (start_dt, end_dt, period_label)."""
    if month and month.strip():
        try:
            year_str, month_str = month.strip().split("-")
            y, m = int(year_str), int(month_str)
            last_day = calendar.monthrange(y, m)[1]
            start_dt = datetime(y, m, 1, 0, 0, 0)
            end_dt = datetime(y, m, last_day, 23, 59, 59)
            return start_dt, end_dt, f"{y}-{m:02d}"
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Định dạng tháng (month) phải là YYYY-MM (VD: 2026-11).",
            )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ngày bắt đầu (start_date) không được lớn hơn ngày kết thúc (end_date).",
        )

    start_dt = datetime.combine(start_date, time.min) if start_date else None
    end_dt = datetime.combine(end_date, time.max) if end_date else None
    label = (
        f"{start_date or 'dau'}_den_{end_date or 'nay'}"
        if (start_date or end_date)
        else "toan-bo"
    )
    return start_dt, end_dt, label


@router.get(
    "/history/{group_id}",
    response_model=PaginatedTransactionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy lịch sử giao dịch quỹ (lọc theo loại, khoảng ngày, người, danh mục, phân trang)",
)
def get_fund_transaction_history(
    group_id: int,
    viewer_id: Optional[int] = Query(None, description="ID người xem (phải trùng JWT)"),
    current_user: User = Depends(get_current_user),
    tx_type: Optional[str] = Query(None, description="INCOME hoặc EXPENSE"),
    start_date: Optional[date] = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    payer_id: Optional[int] = Query(None, description="ID người nộp/chi"),
    category: Optional[str] = Query(None, description="Lọc theo danh mục"),
    status_filter: Optional[str] = Query(None, description="ACTIVE hoặc CANCELLED"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if viewer_id is not None and viewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="viewer_id không khớp tài khoản đăng nhập")
    viewer_id = current_user.id
    _verify_group_member(db, group_id=group_id, viewer_id=viewer_id)

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
        query = query.filter(FundTransaction.occurred_at >= datetime.combine(start_date, time.min))

    if end_date:
        query = query.filter(FundTransaction.occurred_at <= datetime.combine(end_date, time.max))

    if payer_id is not None:
        query = query.filter(FundTransaction.payer_id == payer_id)

    if category and category.strip():
        query = query.filter(FundTransaction.category.ilike(f"%{category.strip()}%"))

    if status_filter and status_filter.strip():
        query = query.filter(FundTransaction.status == status_filter.strip().upper())

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


@router.get(
    "/history/{group_id}/export-csv",
    summary="Task T3CDF02: Xuất CSV lịch sử giao dịch theo kỳ/bộ lọc đang chọn",
)
def export_history_csv(
    group_id: int,
    viewer_id: Optional[int] = Query(None, description="ID người xem (phải trùng JWT)"),
    current_user: User = Depends(get_current_user),
    month: Optional[str] = Query(None, description="Kỳ tháng YYYY-MM (VD: 2026-11)"),
    start_date: Optional[date] = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    tx_type: Optional[str] = Query(None, description="INCOME hoặc EXPENSE"),
    category: Optional[str] = Query(None, description="Lọc theo danh mục"),
    db: Session = Depends(get_db),
):
    if viewer_id is not None and viewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="viewer_id không khớp tài khoản đăng nhập")
    viewer_id = current_user.id
    _verify_group_member(db, group_id=group_id, viewer_id=viewer_id)
    start_dt, end_dt, period_label = _resolve_period_bounds(month, start_date, end_date)

    query = db.query(FundTransaction).filter(FundTransaction.group_id == group_id)
    if start_dt:
        query = query.filter(FundTransaction.occurred_at >= start_dt)
    if end_dt:
        query = query.filter(FundTransaction.occurred_at <= end_dt)
    if tx_type and tx_type.strip().upper() in ("INCOME", "EXPENSE"):
        query = query.filter(FundTransaction.type == tx_type.strip().upper())
    if category and category.strip():
        query = query.filter(FundTransaction.category.ilike(f"%{category.strip()}%"))

    txs = query.order_by(FundTransaction.occurred_at.desc(), FundTransaction.transaction_id.desc()).all()

    output = io.StringIO()
    output.write("\ufeff")  # UTF-8 BOM cho Excel
    writer = csv.writer(output)
    writer.writerow(["Mã GD", "Ngày phát sinh", "Loại", "Danh mục", "Nội dung", "Người nộp/chi (ID)", "Trạng thái", "Số tiền (VND)"])

    for tx in txs:
        amt = int(tx.amount or 0)
        signed_amt = amt if tx.type == "INCOME" else -amt
        writer.writerow([
            f"TX-{tx.transaction_id}",
            tx.occurred_at.strftime("%d/%m/%Y %H:%M") if tx.occurred_at else "",
            "THU" if tx.type == "INCOME" else "CHI",
            tx.category or "",
            tx.description or "",
            tx.payer_id or tx.created_by or "",
            getattr(tx, "status", "ACTIVE") or "ACTIVE",
            signed_amt,
        ])

    filename = f"lich_su_giao_dich_nhom{group_id}_{period_label}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/statement/{group_id}/export-csv",
    summary="Task T3CDF02: Xuất CSV sao kê dòng tiền theo kỳ đang chọn",
)
def export_statement_csv(
    group_id: int,
    viewer_id: Optional[int] = Query(None, description="ID người xem (phải trùng JWT)"),
    current_user: User = Depends(get_current_user),
    month: Optional[str] = Query(None, description="Kỳ tháng YYYY-MM (VD: 2026-11)"),
    start_date: Optional[date] = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    if viewer_id is not None and viewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="viewer_id không khớp tài khoản đăng nhập")
    viewer_id = current_user.id
    _verify_group_member(db, group_id=group_id, viewer_id=viewer_id)
    start_dt, end_dt, period_label = _resolve_period_bounds(month, start_date, end_date)

    # 1. Tính số dư đầu kỳ (trước start_dt)
    opening_balance = 0
    if start_dt:
        prev_txs = (
            db.query(FundTransaction)
            .filter(
                FundTransaction.group_id == group_id,
                FundTransaction.occurred_at < start_dt,
            )
            .all()
        )
        for t in prev_txs:
            if getattr(t, "status", "ACTIVE") == "CANCELLED":
                continue
            opening_balance += int(t.amount or 0) if t.type == "INCOME" else -int(t.amount or 0)

    # 2. Lấy giao dịch trong kỳ
    query = db.query(FundTransaction).filter(FundTransaction.group_id == group_id)
    if start_dt:
        query = query.filter(FundTransaction.occurred_at >= start_dt)
    if end_dt:
        query = query.filter(FundTransaction.occurred_at <= end_dt)
    period_txs = query.order_by(FundTransaction.occurred_at.desc(), FundTransaction.transaction_id.desc()).all()

    total_income = 0
    total_expense = 0
    expense_by_cat = {}

    for t in period_txs:
        if getattr(t, "status", "ACTIVE") == "CANCELLED":
            continue
        amt = int(t.amount or 0)
        if t.type == "INCOME":
            total_income += amt
        else:
            total_expense += amt
            cat = t.category or "Chi chung"
            expense_by_cat[cat] = expense_by_cat.get(cat, 0) + amt

    net_change = total_income - total_expense
    closing_balance = opening_balance + net_change

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["BÁO CÁO SAO KÊ QUỸ NHÓM (SQUAD.CASH)"])
    writer.writerow(["Mã nhóm", f"#GRP-{group_id}"])
    writer.writerow(["Kỳ sao kê", period_label])
    writer.writerow(["Ngày xuất", datetime.utcnow().strftime("%d/%m/%Y %H:%M")])
    writer.writerow([])
    writer.writerow(["1. TỔNG HỢP DÒNG TIỀN TRONG KỲ", "Số tiền (VND)"])
    writer.writerow(["Số dư đầu kỳ", opening_balance])
    writer.writerow(["Tổng thu trong kỳ", total_income])
    writer.writerow(["Tổng chi trong kỳ", total_expense])
    writer.writerow(["Chênh lệch ròng (Thu - Chi)", net_change])
    writer.writerow(["Số dư cuối kỳ", closing_balance])
    writer.writerow([])
    writer.writerow(["2. CƠ CẤU CHI TIÊU THEO DANH MỤC", "Số tiền (VND)", "Tỉ trọng (%)"])
    if expense_by_cat:
        for cat, amt in expense_by_cat.items():
            pct = f"{(amt / total_expense * 100):.1f}%" if total_expense > 0 else "0%"
            writer.writerow([cat, amt, pct])
    else:
        writer.writerow(["Chưa có khoản chi trong kỳ", 0, "0%"])
    writer.writerow([])
    writer.writerow(["3. CHI TIẾT GIAO DỊCH TRONG KỲ"])
    writer.writerow(["Mã GD", "Ngày phát sinh", "Loại", "Danh mục", "Nội dung", "Người nộp/chi (ID)", "Trạng thái", "Số tiền (VND)"])

    for tx in period_txs:
        amt = int(tx.amount or 0)
        signed_amt = amt if tx.type == "INCOME" else -amt
        writer.writerow([
            f"TX-{tx.transaction_id}",
            tx.occurred_at.strftime("%d/%m/%Y %H:%M") if tx.occurred_at else "",
            "THU" if tx.type == "INCOME" else "CHI",
            tx.category or "",
            tx.description or "",
            tx.payer_id or tx.created_by or "",
            getattr(tx, "status", "ACTIVE") or "ACTIVE",
            signed_amt,
        ])

    filename = f"sao_ke_quy_nhom{group_id}_{period_label}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    summary="Host sửa giao dịch quỹ trong vòng 24 giờ kèm lý do (ghi lại lịch sử sửa)",
)
def update_fund_transaction_within_24h(
    transaction_id: int,
    payload: UpdateFundTransactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.role.strip().upper() not in ("HOST", "ADMIN"):
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

    # Client-supplied role/host_id cannot authorize a financial mutation.
    active_host = db.query(GroupMember).filter(
        GroupMember.group_id == tx.group_id,
        GroupMember.user_id == current_user.id,
        GroupMember.role == "HOST",
        GroupMember.status == "ACTIVE",
    ).first()
    if not active_host and current_user.role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ Host của nhóm mới có quyền sửa/hủy giao dịch")

    if getattr(tx, "status", "ACTIVE") == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giao dịch này đã bị huỷ, không thể chỉnh sửa!",
        )

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
            changed_by=current_user.id,
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
    current_user: User = Depends(get_current_user),
):
    if payload.role.strip().upper() not in ("HOST", "ADMIN"):
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

    # Client-supplied role/host_id cannot authorize a financial mutation.
    active_host = db.query(GroupMember).filter(
        GroupMember.group_id == tx.group_id,
        GroupMember.user_id == current_user.id,
        GroupMember.role == "HOST",
        GroupMember.status == "ACTIVE",
    ).first()
    if not active_host and current_user.role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ Host của nhóm mới có quyền sửa/hủy giao dịch")

    if getattr(tx, "status", "ACTIVE") == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giao dịch này đã được huỷ trước đó!",
        )

    _check_within_24_hours(tx)

    try:
        old_snapshot = _snapshot_tx(tx)
        tx.status = "CANCELLED"
        tx.updated_at = datetime.utcnow()
        db.flush()

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
            changed_by=current_user.id,
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
    viewer_id: Optional[int] = Query(None, description="ID người xem (phải trùng JWT)"),
    current_user: User = Depends(get_current_user),
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

    if viewer_id is not None and viewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="viewer_id không khớp tài khoản đăng nhập")
    _verify_group_member(db, group_id=tx.group_id, viewer_id=current_user.id)

    return (
        db.query(FundTransactionLog)
        .filter(FundTransactionLog.transaction_id == transaction_id)
        .order_by(FundTransactionLog.log_id.desc())
        .all()
    )