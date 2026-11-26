from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.Bill import Bill
from app.models.debt_payment import Debt, DebtStatusEnum
from app.models.fund_group import FundGroup
from app.models.FundTransaction import FundTransaction
from app.models.group_member import GroupMember
from app.models.notification import Notification
from app.models.user import SystemRole, User, UserStatus

# Tự động lấy hàm xác thực user hiện tại từ repo Backend
try:
    from app.routers.auth import get_current_user
except ImportError:
    try:
        from app.core.deps import get_current_user
    except ImportError:
        from app.core.security import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class LockUserRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class SoftDeleteGroupRequest(BaseModel):
    reason: Optional[str] = "Nhóm không có giao dịch trong 30 ngày và không còn nợ chưa trả."
    notify_members: bool = True


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_val.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản ADMIN mới có quyền truy cập.",
        )
    return current_user


def _mask_email(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    prefix = local[:3] if len(local) > 3 else local[:1]
    return f"{prefix}***@{domain}"


def _mask_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    if len(phone) <= 6:
        return "***"
    return f"{phone[:3]}***{phone[-3:]}"


def _is_group_deleted(group: FundGroup) -> bool:
    deleted_at = getattr(group, "deleted_at", None)
    if deleted_at is not None:
        return True
    status_val = str(getattr(group, "status", "") or "").upper()
    return status_val in ("DELETED", "SOFT_DELETED")


def _get_group_unpaid_debt(db: Session, group_id: int) -> int:
    debts = (
        db.query(Debt)
        .filter(
            Debt.group_id == group_id,
            Debt.status != DebtStatusEnum.PAID,
        )
        .all()
    )
    total_unpaid = 0
    for d in debts:
        amount = int(d.amount or 0)
        paid = int(d.paid_amount or 0)
        total_unpaid += max(0, amount - paid)
    return total_unpaid


def _get_last_tx_time(db: Session, group_id: int) -> Optional[datetime]:
    return (
        db.query(func.max(FundTransaction.occurred_at))
        .filter(
            FundTransaction.group_id == group_id,
            FundTransaction.status == "ACTIVE",
        )
        .scalar()
    )


# ==================== 1. QUẢN LÝ TÀI KHOẢN ====================
@router.get("/users")
def list_admin_users(
    q: str = Query(""),
    status_filter: str = Query("all", alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    query = db.query(User)

    keyword = q.strip()
    if keyword:
        conditions = [
            User.full_name.ilike(f"%{keyword}%"),
            User.email.ilike(f"%{keyword}%"),
            User.phone.ilike(f"%{keyword}%"),
        ]
        if keyword.isdigit():
            conditions.append(User.id == int(keyword))
        query = query.filter(or_(*conditions))

    sf = status_filter.strip().lower()
    if sf == "active":
        query = query.filter(User.status == UserStatus.ACTIVE)
    elif sf == "locked":
        query = query.filter(User.status == UserStatus.LOCKED)

    total = query.count()
    total_pages = max(1, ceil(total / page_size))
    users = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for u in users:
        group_count = (
            db.query(func.count(GroupMember.id))
            .filter(
                GroupMember.user_id == u.id,
                GroupMember.status == "ACTIVE",
            )
            .scalar()
            or 0
        )
        items.append({
            "id": u.id,
            "full_name": u.full_name,
            "email_masked": _mask_email(u.email),
            "phone_masked": _mask_phone(u.phone),
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "group_count": int(group_count),
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "status": u.status.value if hasattr(u.status, "value") else str(u.status),
            "lock_reason": u.lock_reason,
        })

    return {
        "items": items,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("/users/{user_id}/lock")
def lock_user_account(
    user_id: int,
    payload: LockUserRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    role_val = target.role.value if hasattr(target.role, "value") else str(target.role)
    if role_val.upper() == "ADMIN" or target.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Không thể khóa tài khoản ADMIN.")

    target.status = UserStatus.LOCKED
    target.lock_reason = payload.reason.strip()
    db.commit()
    return {"message": f"Đã khóa tài khoản #{target.id}.", "status": "LOCKED"}


@router.post("/users/{user_id}/unlock")
def unlock_user_account(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    target.status = UserStatus.ACTIVE
    target.lock_reason = None
    db.commit()
    return {"message": f"Đã mở khóa tài khoản #{target.id}.", "status": "ACTIVE"}


# ==================== 2. DASHBOARD KPI + CHART.JS ====================
@router.get("/dashboard")
def get_admin_dashboard(
    period: str = Query("all", pattern="^(all|30d|q4)$"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    now = datetime.utcnow()
    since: Optional[datetime] = None
    if period == "30d":
        since = now - timedelta(days=30)
    elif period == "q4":
        since = datetime(now.year, 10, 1)

    total_users = db.query(func.count(User.id)).scalar() or 0
    locked_users = (
        db.query(func.count(User.id))
        .filter(User.status == UserStatus.LOCKED)
        .scalar()
        or 0
    )
    active_users = max(0, int(total_users) - int(locked_users))

    all_groups = db.query(FundGroup).all()
    active_groups = [g for g in all_groups if not _is_group_deleted(g)]

    bill_q = db.query(func.count(Bill.id)).filter(Bill.status != "CANCELLED")
    tx_q = db.query(func.coalesce(func.sum(FundTransaction.amount), 0)).filter(
        FundTransaction.status == "ACTIVE"
    )
    if since:
        bill_q = bill_q.filter(Bill.created_at >= since)
        tx_q = tx_q.filter(FundTransaction.occurred_at >= since)

    total_bills = bill_q.scalar() or 0
    total_transaction_amount = tx_q.scalar() or 0

    # Nhóm mới theo tháng (YYYY-MM)
    monthly_counter = defaultdict(int)
    for g in active_groups:
        ref_dt = g.created_at or _get_last_tx_time(db, g.id) or now
        if since and ref_dt < since:
            continue
        monthly_counter[ref_dt.strftime("%Y-%m")] += 1

    monthly_new_groups = [
        {"month": month, "count": monthly_counter[month]}
        for month in sorted(monthly_counter.keys())
    ]

    # Đếm nhóm không có giao dịch trong 30 ngày gần nhất
    cutoff_30d = now - timedelta(days=30)
    inactive_30d_count = 0
    for g in active_groups:
        last_tx = _get_last_tx_time(db, g.id)
        if last_tx is None or last_tx < cutoff_30d:
            inactive_30d_count += 1

    return {
        "synced_at": now.isoformat() + "Z",
        "period": period,
        "kpis": {
            "total_users": int(total_users),
            "active_users": int(active_users),
            "locked_users": int(locked_users),
            "total_groups": len(active_groups),
            "total_bills": int(total_bills),
            "total_transaction_amount": int(total_transaction_amount),
            "inactive_30d_count": int(inactive_30d_count),
        },
        "monthly_new_groups": monthly_new_groups,
    }


# ==================== 3. NHÓM KHÔNG GD 30 NGÀY & XÓA MỀM ====================
@router.get("/groups")
def get_admin_groups(
    filter: str = Query("inactive_30d", pattern="^(inactive_30d|all|active|soft_deleted)$"),
    q: str = Query(""),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    now = datetime.utcnow()
    cutoff_30d = now - timedelta(days=30)
    keyword = q.strip().lower()

    groups = db.query(FundGroup).order_by(FundGroup.id.desc()).all()
    items = []

    for g in groups:
        is_deleted = _is_group_deleted(g)
        last_tx = _get_last_tx_time(db, g.id)
        is_inactive_30d = (not is_deleted) and (last_tx is None or last_tx < cutoff_30d)

        if filter == "inactive_30d" and not is_inactive_30d:
            continue
        if filter == "active" and is_deleted:
            continue
        if filter == "soft_deleted" and not is_deleted:
            continue

        if keyword and keyword not in (g.name or "").lower() and keyword not in str(g.id):
            continue

        member_count = (
            db.query(func.count(GroupMember.id))
            .filter(
                GroupMember.group_id == g.id,
                GroupMember.status == "ACTIVE",
            )
            .scalar()
            or 0
        )

        host_user = (
            db.query(User)
            .join(GroupMember, GroupMember.user_id == User.id)
            .filter(
                GroupMember.group_id == g.id,
                func.upper(GroupMember.role) == "HOST",
            )
            .first()
        )
        if not host_user:
            host_user = db.query(User).filter(User.id == g.creator_id).first()

        unpaid_debt = _get_group_unpaid_debt(db, g.id)

        items.append({
            "id": g.id,
            "name": g.name,
            "host_name": host_user.full_name if host_user else "—",
            "member_count": int(member_count),
            "last_transaction_at": last_tx.isoformat() if last_tx else None,
            "last_activity_at": (last_tx or g.created_at).isoformat() if (last_tx or g.created_at) else None,
            "unpaid_debt": int(unpaid_debt),
            "is_deleted": is_deleted,
            "status": "soft_deleted" if is_deleted else "active",
            "can_soft_delete": (not is_deleted) and unpaid_debt == 0,
        })

    return {"total": len(items), "items": items}


@router.delete("/groups/{group_id}")
def soft_delete_admin_group(
    group_id: int,
    payload: Optional[SoftDeleteGroupRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    group = db.query(FundGroup).filter(FundGroup.id == group_id).first()
    if not group or _is_group_deleted(group):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhóm hoặc nhóm đã bị xóa mềm trước đó.",
        )

    unpaid_debt = _get_group_unpaid_debt(db, group_id)
    if unpaid_debt > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa mềm nhóm '{group.name}' vì vẫn còn nợ chưa trả ({unpaid_debt:,} ₫).",
        )

    # 1. Xóa mềm nhóm
    group.status = "SOFT_DELETED"
    group.deleted_at = datetime.utcnow()

    # 2. Gửi thông báo cho toàn bộ thành viên trong nhóm
    notified_count = 0
    should_notify = payload.notify_members if payload else True
    reason_text = (
        payload.reason.strip()
        if payload and payload.reason
        else "Nhóm không có giao dịch trong 30 ngày và đã tất toán toàn bộ nợ."
    )

    if should_notify:
        members = (
            db.query(GroupMember)
            .filter(
                GroupMember.group_id == group_id,
                GroupMember.status == "ACTIVE",
            )
            .all()
        )
        member_user_ids = {m.user_id for m in members}
        if group.creator_id:
            member_user_ids.add(group.creator_id)

        for uid in member_user_ids:
            db.add(
                Notification(
                    user_id=uid,
                    title="Nhóm quỹ đã bị xóa mềm",
                    message=f"Nhóm '{group.name}' đã được Admin xóa mềm. Lý do: {reason_text}",
                    is_read=False,
                )
            )
            notified_count += 1

    db.commit()
    return {
        "message": f"Đã xóa mềm nhóm '{group.name}' và gửi thông báo tới {notified_count} thành viên.",
        "group_id": group_id,
        "notified_members": notified_count,
    }