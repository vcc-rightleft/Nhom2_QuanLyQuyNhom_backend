
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import Base, engine


# ==============================
# IMPORT MODELS
# ==============================

from app.models.user import User
from app.models.fund_group import FundGroup
from app.models.group_member import GroupMember
from app.models.notification import Notification
from app.models.Bill import Bill
from app.models.Bill_share import BillShare
from app.models.FundTransaction import FundTransaction
from app.models.Collection import CollectionCampaign, MemberDebt


# ==============================
# IMPORT ROUTERS
# ==============================

from app.routers import (
    auth,
    bill,
    bills,
    bill_split,
    collection,
    debt,
    expense,
    fund,
    health,
    items,
    notification,
    transaction_history,
    user,
    admin,
)

from app.routers.groups import router as groups_router


# ==============================
# KHỞI TẠO DATABASE
# ==============================

Base.metadata.create_all(bind=engine)


# ==============================
# KHỞI TẠO FASTAPI
# ==============================

app = FastAPI(
    title="Nhóm 2 - Quản Lý Quỹ Nhóm API",
    docs_url="/docs",
)


# ==============================
# CẤU HÌNH CORS
# ==============================

cors_origins = (
    ["*"]
    if settings.CORS_ORIGINS.strip() == "*"
    else [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# ĐĂNG KÝ ROUTERS
# ==============================

# Kiểm tra trạng thái hệ thống
app.include_router(health.router, prefix="/api")

# Xác thực tài khoản
app.include_router(auth.router)

# Quản lý nhóm
app.include_router(groups_router, prefix="/api")

# Quản lý quỹ
app.include_router(fund.router, prefix="/api")

# Quản lý công nợ
app.include_router(debt.router, prefix="/api")

# Quản lý hóa đơn
app.include_router(bill.router, prefix="/api")
app.include_router(bills.router, prefix="/api")

# Chia hóa đơn
app.include_router(bill_split.router, prefix="/api")

# Lịch sử giao dịch và sao kê
app.include_router(transaction_history.router, prefix="/api")

# Quản lý người dùng
app.include_router(user.router)

# Quản trị Admin - T3CCB5B
app.include_router(admin.router)


# ==============================
# PHỤC VỤ GIAO DIỆN FRONTEND
# ==============================

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "frontend",
)

if os.path.isdir(FRONTEND_DIR):
    app.mount(
        "/frontend",
        StaticFiles(
            directory=FRONTEND_DIR,
            html=True,
        ),
        name="frontend",
    )


@app.get("/ui", include_in_schema=False)
@app.get("/quy-chung", include_in_schema=False)
def serve_fund_tab_ui():
    """
    Phục vụ giao diện nếu thư mục frontend
    được đặt bên trong Backend.
    """

    index_path = os.path.join(
        FRONTEND_DIR,
        "index.html",
    )

    if not os.path.isfile(index_path):
        raise HTTPException(
            status_code=404,
            detail=(
                "Không tìm thấy thư mục frontend trong Backend. "
                "Hãy chạy server Frontend riêng."
            ),
        )

    return FileResponse(index_path)


# ==============================
# ROOT API
# ==============================

@app.get("/")
def root():
    return {
        "message": "Server đang chạy.",
        "ui_tab_quy_chung": "/ui",
        "docs": "/docs",
    }
