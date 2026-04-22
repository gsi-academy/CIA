from fastapi import FastAPI
from app.database import engine, Base

# WAJIB ADA INI (BIAR TABEL TERDETEKSI)
from app.models import models_v2

from app.routes.auth import router as auth_router
from app.routes.reports import router as report_router
from app.routes.dashboard import router as dashboard_router
from app.routes.history import router as history_router
from app.routes.master import router as master_router
from app.routes.export import router as export_router
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
app.include_router(report_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(history_router, prefix=API_PREFIX)
app.include_router(master_router, prefix=API_PREFIX)
app.include_router(export_router, prefix="/api/v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mengizinkan semua domain (termasuk file lokal)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)