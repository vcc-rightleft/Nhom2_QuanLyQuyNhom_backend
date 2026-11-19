import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import Base, engine
from app.models.user import User
from app.models.notification import Notification
from app.models.bill import Bill
from app.models.Bill_share import BillShare
from app.routers import (
    auth,
    bill,
    bill_split,
    collection,
    debt,
    expense,
    health,
    items,
    notification,
    transaction_history,
    user,
)
from app.routers.groups import router as groups_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nhóm 2 - Quản Lý Quỹ Nhóm API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn các router nghiệp vụ
app.include_router(health.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(auth.router)
app.include_router(groups_router, prefix="/api")
app.include_router(debt.router, prefix="/api")
app.include_router(debt.router)
app.include_router(notification.router, prefix="/api")
app.include_router(notification.router)
app.include_router(bill.router, prefix="/api")
app.include_router(user.router)
app.include_router(collection.router)
app.include_router(expense.router, prefix="/api")
app.include_router(bill_split.router, prefix="/api")
app.include_router(transaction_history.router, prefix="/api")

# Phục vụ giao diện [UI] Tab Quỹ chung (T3CCFBA)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/ui", include_in_schema=False)
@app.get("/quy-chung", include_in_schema=False)
def serve_fund_tab_ui():
    """Trả về giao diện [UI] Tab Quỹ chung (T3CCFBA)."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index_path)


@app.get("/")
def root():
    return {
        "message": "Server đang chạy.",
        "ui_tab_quy_chung": "/ui",
        "docs": "/docs",
    }