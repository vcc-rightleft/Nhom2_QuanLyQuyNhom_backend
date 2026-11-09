import bcrypt
from sqlalchemy.orm import Session
from app.models.user import User, SystemRole, UserStatus


def hash_password_bcrypt(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


SEED_USERS_DATA = [
    # 01 Tài khoản Admin hệ thống
    {
        "email": "admin@moneymate.vn",
        "password": "Admin@123",
        "full_name": "Phan Đức Anh (Admin)",
        "phone": "0901000001",
        "avatar_url": "https://ui-avatars.com/api/?name=Phan+Duc+Anh&background=1E3A8A&color=fff",
        "bank_name": "Vietcombank",
        "bank_account_no": "1029384756",
        "bank_account_name": "PHAN DUC ANH",
        "role": SystemRole.ADMIN,
        "status": UserStatus.ACTIVE,
    },
    # 10 Tài khoản User mẫu (Host là vai trò trong từng nhóm, không phải role hệ thống)
    {
        "email": "user1@moneymate.vn",
        "password": "User@123",
        "full_name": "Nguyễn Minh Quân",
        "phone": "0901000002",
        "bank_name": "MB Bank",
        "bank_account_no": "0901000002",
        "bank_account_name": "NGUYEN MINH QUAN",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user2@moneymate.vn",
        "password": "User@123",
        "full_name": "Trần Quốc Thắng",
        "phone": "0901000003",
        "bank_name": "Techcombank",
        "bank_account_no": "1903888999",
        "bank_account_name": "TRAN QUOC THANG",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user3@moneymate.vn",
        "password": "User@123",
        "full_name": "Lê Bảo Quốc",
        "phone": "0901000004",
        "bank_name": "BIDV",
        "bank_account_no": "31410001234567",
        "bank_account_name": "LE BAO QUOC",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user4@moneymate.vn",
        "password": "User@123",
        "full_name": "Phạm Thu Hà",
        "phone": "0901000005",
        "bank_name": "ACB",
        "bank_account_no": "88991122",
        "bank_account_name": "PHAM THU HA",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user5@moneymate.vn",
        "password": "User@123",
        "full_name": "Hoàng Gia Huy",
        "phone": "0901000006",
        "bank_name": "VPBank",
        "bank_account_no": "6677889900",
        "bank_account_name": "HOANG GIA HUY",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user6@moneymate.vn",
        "password": "User@123",
        "full_name": "Vũ Khánh Linh",
        "phone": "0901000007",
        "bank_name": "TPBank",
        "bank_account_no": "04567891234",
        "bank_account_name": "VU KHANH LINH",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user7@moneymate.vn",
        "password": "User@123",
        "full_name": "Đỗ Tuấn Kiệt",
        "phone": "0901000008",
        "bank_name": "VietinBank",
        "bank_account_no": "105876543210",
        "bank_account_name": "DO TUAN KIET",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user8@moneymate.vn",
        "password": "User@123",
        "full_name": "Bùi Phương Thảo",
        "phone": "0901000009",
        "bank_name": "VIB",
        "bank_account_no": "601234567",
        "bank_account_name": "BUI PHUONG THAO",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user9@moneymate.vn",
        "password": "User@123",
        "full_name": "Đặng Quốc Việt",
        "phone": "0901000010",
        "bank_name": "Sacombank",
        "bank_account_no": "060987654321",
        "bank_account_name": "DANG QUOC VIET",
        "role": SystemRole.USER,
        "status": UserStatus.ACTIVE,
    },
    {
        "email": "user10@moneymate.vn",
        "password": "User@123",
        "full_name": "Ngô Thanh Tùng",
        "phone": "0901000011",
        "bank_name": "Agribank",
        "bank_account_no": "1500205999888",
        "bank_account_name": "NGO THANH TUNG",
        "role": SystemRole.USER,
        "status": UserStatus.LOCKED,
        "lock_reason": "Tài khoản mẫu bị khóa để kiểm thử chặn đăng nhập",
    },
]


def seed_users(db: Session) -> None:
    """Seed 1 Admin và 10 User vào bảng users nếu chưa tồn tại."""
    for item in SEED_USERS_DATA:
        exists = db.query(User).filter(User.email == item["email"]).first()
        if not exists:
            user = User(
                email=item["email"],
                password_hash=hash_password_bcrypt(item["password"]),
                full_name=item["full_name"],
                phone=item.get("phone"),
                avatar_url=item.get(
                    "avatar_url",
                    f"https://ui-avatars.com/api/?name={item['full_name']}&background=2563EB&color=fff",
                ),
                bank_name=item.get("bank_name"),
                bank_account_no=item.get("bank_account_no"),
                bank_account_name=item.get("bank_account_name"),
                role=item["role"],
                status=item["status"],
                lock_reason=item.get("lock_reason"),
            )
            db.add(user)
    db.commit()