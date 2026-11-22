from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.group import GroupCreate
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
    current_user: User = Depends(get_current_user),
):
    return create_group(
        db=db,
        group=group,
        user_id=current_user.id,
    )


@router.post("/join")
def join_group_by_code(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return join_group(
        db=db,
        invite_code=invite_code,
        user_id=current_user.id,
    )


@router.get("/my-groups")
def my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_groups(
        db=db,
        user_id=current_user.id,
    )


@router.get("/{group_id}")
def group_detail(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_group_detail(
        db=db,
        group_id=group_id,
    )


@router.get("/{group_id}/members")
def group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_group_members(
        db=db,
        group_id=group_id,
    )


@router.post("/{group_id}/leave")
def leave(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return leave_group(
        db=db,
        group_id=group_id,
        user_id=current_user.id,
    )


@router.post("/{group_id}/transfer-host")
def transfer(
    group_id: int,
    new_host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return transfer_host(
        db=db,
        group_id=group_id,
        current_host_id=current_user.id,
        new_host_id=new_host_id,
    )


@router.delete("/{group_id}/members/{member_id}")
def remove(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return remove_member(
        db=db,
        group_id=group_id,
        host_id=current_user.id,
        member_id=member_id,
    )