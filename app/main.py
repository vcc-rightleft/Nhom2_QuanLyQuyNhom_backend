from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import health, items
from app.routers import debt

app = FastAPI(title="Base API", docs_url="/docs")
app.include_router(debt.router)

# Mở CORS cho phép Frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn router
app.include_router(health.router, prefix="/api")
app.include_router(items.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Server đang chạy."}