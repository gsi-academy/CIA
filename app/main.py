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

# QUICK FIX: Migrasi kolom yang hilang (birth_info, address, guardian_name, musyrif_id)
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE santri ADD COLUMN IF NOT EXISTS birth_info VARCHAR"))
        conn.execute(text("ALTER TABLE santri ADD COLUMN IF NOT EXISTS address TEXT"))
        conn.execute(text("ALTER TABLE santri ADD COLUMN IF NOT EXISTS guardian_name VARCHAR"))
        conn.execute(text("ALTER TABLE santri ADD COLUMN IF NOT EXISTS musyrif_id UUID REFERENCES users(id)"))
        conn.execute(text("ALTER TABLE kms_main_indicators ADD COLUMN IF NOT EXISTS weight FLOAT DEFAULT 1.0"))
        conn.commit()
    except Exception as e:
        print(f"Migration notice: {e}")

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