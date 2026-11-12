import random
import string

from sqlalchemy.orm import Session

from app.models.fund_group import FundGroup
from app.models.group_member import GroupMember
from app.schemas.group import GroupCreate


def generate_invite_code():
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=8
        )
    )


def create_group(db: Session, group: GroupCreate):

    invite_code = generate_invite_code()

    db_group = FundGroup(
        name=group.name,
        description=group.description,
        image_url=group.image_url,
        invite_code=invite_code,
        status="ACTIVE",
        creator_id=1
    )

    db.add(db_group)
    db.commit()
    db.refresh(db_group)

    host = GroupMember(
        group_id=db_group.id,
        user_id=1,
        role="HOST",
        status="ACTIVE"
    )

    db.add(host)
    db.commit()

    return {
        "id": db_group.id,
        "name": db_group.name,
        "description": db_group.description,
        "image_url": db_group.image_url,
        "invite_code": db_group.invite_code,
        "status": db_group.status,
        "message": "Tạo nhóm thành công"
    }


def join_group(db: Session, invite_code: str, user_id: int):

    group = db.query(FundGroup).filter(
        FundGroup.invite_code == invite_code
    ).first()

    if not group:
        return {
            "message": "Không tìm thấy mã mời"
        }

    if group.status == "ARCHIVED":
        return {
            "message": "Nhóm đã ARCHIVED"
        }

    existed = db.query(GroupMember).filter(
        GroupMember.group_id == group.id,
        GroupMember.user_id == user_id
    ).first()

    if existed:
        return {
            "message": "Bạn đã tham gia nhóm"
        }

    member = GroupMember(
        group_id=group.id,
        user_id=user_id,
        role="MEMBER",
        status="ACTIVE"
    )

    db.add(member)
    db.commit()

    return {
        "message": "Tham gia nhóm thành công",
        "group_id": group.id,
        "group_name": group.name,
        "user_id": user_id
    }
