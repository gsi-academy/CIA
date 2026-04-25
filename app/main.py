from fastapi import FastAPI
from app.database import engine, Base

# WAJIB ADA INI (BIAR TABEL TERDETEKSI)
from app.models import models

from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.user import router as user_router
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CIA API (Core Intelligence Analysis)",
    description="Backend service for CIA Intelligence Reporting System - Role Based Access",
    version="2.0.0"
)

# =========================
# HEALTH CHECK
# =========================
@app.get("/api/v1/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "cia-api", "version": "2.0.0"}


# BUAT SEMUA TABEL
Base.metadata.create_all(bind=engine)

# =========================
# API VERSIONING PREFIX
# =========================
API_PREFIX = "/api/v1"

# =========================
# REGISTER ROUTER
# =========================
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(user_router, prefix=API_PREFIX)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mengizinkan semua domain (termasuk file lokal)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)