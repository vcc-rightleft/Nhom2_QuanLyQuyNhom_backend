from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.group import create_group, join_group
from app.schemas.group import GroupCreate

from app.crud.group import (
    get_my_groups,
    get_group_detail,
    get_group_members
)
from app.crud.group import (
    leave_group,
    transfer_host,
    remove_member
)

router = APIRouter(
    prefix="/groups",
    tags=["Groups"]
)

@router.post("/")
def create_new_group(
    group: GroupCreate,
    db: Session = Depends(get_db)
):
    # Đảm bảo tạo nhóm cũng dùng user 1
    return create_group(db, group)

@router.post("/join")
def join_group_by_code(
    invite_code: str,
    db: Session = Depends(get_db)
):
    return join_group(
        db=db,
        invite_code=invite_code,
        user_id=1  # <--- Đã đổi thành 1 để khớp với my-groups
    )   

@router.get("/my-groups")
def my_groups(
    db: Session = Depends(get_db)
):
    return get_my_groups(
        db=db,
        user_id=1
    )

@router.get("/{group_id}")
def group_detail(
    group_id: int,
    db: Session = Depends(get_db)
):
    return get_group_detail(
        db=db,
        group_id=group_id
    )

@router.get("/{group_id}/members")
def group_members(
    group_id: int,
    db: Session = Depends(get_db)
):
    return get_group_members(
        db=db,
        group_id=group_id
    )

#task T3CCB18

@router.post("/{group_id}/leave")
def leave(
    group_id: int,
    db: Session = Depends(get_db)
):
    return leave_group(
        db=db,
        group_id=group_id,
        user_id=1
    )

@router.post("/{group_id}/transfer-host")
def transfer(
    group_id: int,
    new_host_id: int,
    db: Session = Depends(get_db)
):
    return transfer_host(
        db=db,
        group_id=group_id,
        current_host_id=1,
        new_host_id=new_host_id
    )

@router.delete("/{group_id}/members/{member_id}")
def remove(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db)
):
    return remove_member(
        db=db,
        group_id=group_id,
        host_id=1,
        member_id=member_id
    )