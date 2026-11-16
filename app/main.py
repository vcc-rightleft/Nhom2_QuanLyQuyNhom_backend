from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health, items, auth
from app.db.session import engine
from app.models.user import User, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Base API", docs_url="/docs")
from app.db.session import engine, Base
from app.models.user import User  # Import để SQLAlchemy nhận diện model

from app.routers import health, items
from app.routers.groups import router as groups_router

from app.routers import debt

app = FastAPI(title="Base API", docs_url="/docs")
app.include_router(debt.router)

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


@app.get("/")
def root():
    return {"message": "Server đang chạy."}