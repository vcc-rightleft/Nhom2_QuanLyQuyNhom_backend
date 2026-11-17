from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, engine
from app.models.user import User
from app.models.notification import Notification
from app.routers import auth, debt, health, items, notification, user
from app.routers.groups import router as groups_router
from app.models.Bill import Bill
from app.models.Bill_share import BillShare
from app.routers import auth, debt, health, items, notification, bill

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Quản Lý Quỹ Nhóm API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(auth.router)
app.include_router(groups_router, prefix="/api")
app.include_router(debt.router, prefix="/api")
app.include_router(notification.router, prefix="/api")
app.include_router(bill.router, prefix="/api")
app.include_router(user.router)
@app.get("/")
def root():
    return {"message": "Server đang chạy."}