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

router = APIRouter(
    prefix="/groups",
    tags=["Groups"]
)


@router.post("/")
def create_new_group(
    group: GroupCreate,
    db: Session = Depends(get_db)
):
    return create_group(db, group)


@router.post("/join")
def join_group_by_code(
    invite_code: str,
    db: Session = Depends(get_db)
):
    return join_group(
        db=db,
        invite_code=invite_code,
        user_id=2
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