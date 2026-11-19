import random
import string

from sqlalchemy.orm import Session

from app.models.fund_group import FundGroup
from app.models.group_member import GroupMember
from app.schemas.group import GroupCreate
from app.models.debt_payment import Debt, DebtStatusEnum


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
def get_my_groups(db: Session, user_id: int):

    memberships = db.query(GroupMember).filter(
        GroupMember.user_id == user_id
    ).all()

    result = []

    for membership in memberships:

        group = db.query(FundGroup).filter(
            FundGroup.id == membership.group_id
        ).first()

        member_count = db.query(GroupMember).filter(
            GroupMember.group_id == group.id
        ).count()

        result.append({
            "group_id": group.id,
            "group_name": group.name,
            "role": membership.role,
            "member_count": member_count,
            "fund_balance": 0
        })

    return result
def get_group_detail(db: Session, group_id: int):

    group = db.query(FundGroup).filter(
        FundGroup.id == group_id
    ).first()

    if not group:
        return None

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "invite_code": group.invite_code,
        "status": group.status
    }

def get_group_members(db: Session, group_id: int):

    members = db.query(GroupMember).filter(
        GroupMember.group_id == group_id
    ).all()

    result = []

    for member in members:
        result.append({
            "user_id": member.user_id,
            "role": member.role,
            "status": member.status
        })

    return result
# task T3CCB18
def has_unpaid_debt(db: Session, user_id: int, group_id: int):

    debt = db.query(Debt).filter(
        Debt.group_id == group_id,
        Debt.status != DebtStatusEnum.PAID,
        (
            (Debt.debtor_id == user_id) |
            (Debt.payee_id == user_id)
        )
    ).first()

    return debt is not None

def leave_group(
    db: Session,
    group_id: int,
    user_id: int
):

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()

    if not member:
        return {
            "message": "Thành viên không tồn tại trong nhóm"
        }

    if has_unpaid_debt(db, user_id, group_id):
        return {
            "message": "Không thể rời nhóm khi còn công nợ"
        }

    if member.role == "HOST":
        return {
            "message": "Host phải chuyển quyền trước khi rời nhóm"
        }

    db.delete(member)
    db.commit()

    return {
        "message": "Rời nhóm thành công"
    }

def transfer_host(
    db: Session,
    group_id: int,
    current_host_id: int,
    new_host_id: int
):

    current_host = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_host_id,
        GroupMember.role == "HOST"
    ).first()

    if not current_host:
        return {
            "message": "Bạn không phải HOST"
        }

    new_host = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == new_host_id
    ).first()

    if not new_host:
        return {
            "message": "Thành viên không thuộc nhóm"
        }

    current_host.role = "MEMBER"
    new_host.role = "HOST"

    db.commit()

    return {
        "message": "Chuyển quyền HOST thành công"
    }

def remove_member(
    db: Session,
    group_id: int,
    host_id: int,
    member_id: int
):

    host = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == host_id,
        GroupMember.role == "HOST"
    ).first()

    if not host:
        return {
            "message": "Chỉ HOST mới được xóa thành viên"
        }

    if host_id == member_id:
        return {
            "message": "Không thể tự xóa chính mình"
        }

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == member_id
    ).first()

    if not member:
        return {
            "message": "Không tìm thấy thành viên"
        }

    if has_unpaid_debt(db, member_id, group_id):
        return {
            "message": "Không thể xóa thành viên còn công nợ"
        }

    db.delete(member)
    db.commit()

    return {
        "message": "Xóa thành viên thành công"
    }