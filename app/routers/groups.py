from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.group import create_group, join_group
from app.schemas.group import GroupCreate

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