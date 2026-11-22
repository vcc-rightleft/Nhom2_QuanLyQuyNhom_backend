from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.group import GroupCreate
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.group_member import GroupMember
from app.models.debt_payment import Debt
from app.core.deps import require_group_host

from app.crud.group import (
    create_group,
    join_group,
    get_my_groups,
    get_group_detail,
    get_group_members,
    leave_group,
    transfer_host,
    remove_member,
)

router = APIRouter(
    prefix="/groups",
    tags=["Groups"],
)


@router.post("/")
def create_new_group(
    group: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_group(db, group, current_user.id)

@router.post("/join")
def join_group_by_code(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return join_group(
        db=db,
        invite_code=invite_code,
        user_id=current_user.id
    )   

@router.get("/my-groups")
def my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_my_groups(
        db=db,
        user_id=current_user.id
    )


@router.get("/{group_id}")
def group_detail(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ensure_member(db, group_id, current_user.id)
    return get_group_detail(
        db=db,
        group_id=group_id,
    )


@router.get("/{group_id}/members")
def group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ensure_member(db, group_id, current_user.id)
    return get_group_members(
        db=db,
        group_id=group_id,
    )


@router.post("/{group_id}/leave")
def leave(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return leave_group(
        db=db,
        group_id=group_id,
        user_id=current_user.id
    )


@router.post("/{group_id}/transfer-host")
def transfer(
    group_id: int,
    new_host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return transfer_host(
        db=db,
        group_id=group_id,
        current_host_id=current_user.id,
        new_host_id=new_host_id
    )


@router.delete("/{group_id}/members/{member_id}")
def remove(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return remove_member(
        db=db,
        group_id=group_id,
        host_id=current_user.id,
        member_id=member_id
    )

def ensure_member(db: Session, group_id: int, user_id: int):
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id,
        GroupMember.status == "ACTIVE"
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Bạn không thuộc nhóm này")
    return member


@router.get("/{group_id}/debts")
def group_debts_for_host(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_group_host),
):
    """Host lấy toàn bộ công nợ của nhóm; không tin user_id do client cung cấp."""
    from app.models.user import User as UserModel
    debts = db.query(Debt).filter(Debt.group_id == group_id).order_by(Debt.id.desc()).all()
    ids = list({d.debtor_id for d in debts} | {d.payee_id for d in debts})
    users = db.query(UserModel).filter(UserModel.id.in_(ids)).all() if ids else []
    names = {u.id: u.full_name for u in users}
    return [{
        "id": d.id, "group_id": d.group_id,
        "debtor_id": d.debtor_id, "debtor_name": names.get(d.debtor_id, f"User #{d.debtor_id}"),
        "payee_id": d.payee_id, "payee_name": names.get(d.payee_id, f"User #{d.payee_id}"),
        "source_type": d.source_type.value if hasattr(d.source_type, "value") else str(d.source_type),
        "amount": int(d.amount), "paid_amount": int(d.paid_amount or 0),
        "status": d.status.value if hasattr(d.status, "value") else str(d.status),
        "created_at": d.created_at.isoformat() if d.created_at else None,
    } for d in debts]
