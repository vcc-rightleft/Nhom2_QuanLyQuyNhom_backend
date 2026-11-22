"""FR-ADM-001/002/003: authenticated system-administrator account management."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, SystemRole, UserStatus
from app.models.group_member import GroupMember
from app.models.admin_account_audit import AdminAccountAudit
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/admin/users", tags=["Admin - Accounts"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên hệ thống mới có quyền truy cập.")
    return user


def mask_email(value: str | None) -> str:
    if not value or "@" not in value:
        return ""
    name, domain = value.split("@", 1)
    return name[:2] + "***@" + domain


def mask_phone(value: str | None) -> str:
    if not value:
        return ""
    return ("*" * max(len(value)-3, 0)) + value[-3:]


class LockRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class AccountOut(BaseModel):
    id: int
    full_name: str
    email_masked: str
    phone_masked: str
    role: str
    status: str
    created_at: datetime
    group_count: int
    lock_reason: str | None = None


class AccountListOut(BaseModel):
    items: list[AccountOut]
    page: int
    page_size: int
    total: int
    total_pages: int


def account_out(user: User, group_count: int) -> AccountOut:
    return AccountOut(
        id=user.id, full_name=user.full_name,
        email_masked=mask_email(user.email), phone_masked=mask_phone(user.phone),
        role=user.role.value, status=user.status.value,
        created_at=user.created_at, group_count=group_count,
        lock_reason=user.lock_reason,
    )


@router.get("", response_model=AccountListOut)
def list_accounts(
    q: str = Query(default="", max_length=150),
    account_status: Literal["all", "active", "locked"] = Query(default="all", alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(User)
    search = q.strip()
    if search:
        conditions = [
            User.full_name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.phone.ilike(f"%{search}%"),
        ]
        if search.isdecimal():
            conditions.append(User.id == int(search))
        query = query.filter(or_(*conditions))
    if account_status != "all":
        query = query.filter(User.status == (UserStatus.ACTIVE if account_status == "active" else UserStatus.LOCKED))
    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    ids = [u.id for u in users]
    counts = {}
    if ids:
        counts = dict(
            db.query(GroupMember.user_id, func.count(func.distinct(GroupMember.group_id)))
              .filter(GroupMember.user_id.in_(ids), GroupMember.status == "ACTIVE")
              .group_by(GroupMember.user_id).all()
        )
    return AccountListOut(
        items=[account_out(u, counts.get(u.id, 0)) for u in users],
        page=page, page_size=page_size, total=total,
        total_pages=(total + page_size - 1)//page_size,
    )


@router.post("/{user_id}/lock", response_model=AccountOut)
def lock_account(
    user_id: int,
    payload: LockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if target.role == SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Không cho phép khóa tài khoản quản trị viên.")
    if target.status == UserStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Tài khoản đã bị khóa.")
    reason = payload.reason.strip()
    if len(reason) < 5:
        raise HTTPException(status_code=422, detail="Lý do khóa phải có ít nhất 5 ký tự.")
    target.status = UserStatus.LOCKED
    target.lock_reason = reason
    target.token_version = int(target.token_version or 0) + 1
    db.add(AdminAccountAudit(actor_id=admin.id, target_user_id=target.id, action="LOCK", reason=reason))
    db.commit()
    db.refresh(target)
    return account_out(target, db.query(func.count(func.distinct(GroupMember.group_id))).filter(GroupMember.user_id == target.id, GroupMember.status == "ACTIVE").scalar() or 0)


@router.post("/{user_id}/unlock", response_model=AccountOut)
def unlock_account(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if target.role == SystemRole.ADMIN:
        raise HTTPException(status_code=403, detail="Không cho phép thay đổi trạng thái tài khoản quản trị viên.")
    if target.status == UserStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Tài khoản đang hoạt động.")
    target.status = UserStatus.ACTIVE
    target.lock_reason = None
    target.token_version = int(target.token_version or 0) + 1
    db.add(AdminAccountAudit(actor_id=admin.id, target_user_id=target.id, action="UNLOCK"))
    db.commit()
    db.refresh(target)
    return account_out(target, db.query(func.count(func.distinct(GroupMember.group_id))).filter(GroupMember.user_id == target.id, GroupMember.status == "ACTIVE").scalar() or 0)


class AuditOut(BaseModel):
    id: int
    actor_id: int
    target_user_id: int
    action: str
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/{user_id}/audit", response_model=list[AuditOut])
def account_audit(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return db.query(AdminAccountAudit).filter(AdminAccountAudit.target_user_id == user_id).order_by(AdminAccountAudit.id.desc()).limit(100).all()
