from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.models_v2 import (
    Report,
    ReportAnalysis,
    ReportParameterDetection,
    KMSProfile,
    Student
)
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

from app.core.alerts import check_and_alert
from app.schemas.report import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# =========================
# DB SESSION
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# AUTH
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


# =========================
# DASHBOARD SANTRI
# =========================

@router.get(
    "/santri/{santri_id}",
    response_model=DashboardResponse,
    summary="Dashboard Santri",
    description="Mengambil ringkasan performa santri berdasarkan akumulasi parameter KMS yang tercapai."
)
def get_santri_dashboard(
    santri_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Ambil profile (skor sudah dihitung di process_ai)
    profile = db.query(KMSProfile).filter(KMSProfile.santri_id == santri_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=404, 
            detail="Belum ada data AI untuk santri ini. Pastikan laporan sudah di-verify."
        )

    # Logika Trend (Simple based on profile overall score vs baseline 50)
    avg = profile.overall_score
    if avg > 75:
        trend = "improving"
    elif avg < 40:
        trend = "declining"
    else:
        trend = "stable"

    santri = db.query(Student).filter(Student.id == santri_id).first()
    alert_message = check_and_alert(santri.name if santri else "Unknown", trend, avg)

    return {
        "santri_id": santri_id,
        "total_reports": profile.report_count,
        "average_score": avg, # Ini sekarang adalah overall KMS percentage
        "trend": trend,
        "alert": alert_message,
        "detail_scores": {
            "karakter": profile.karakter_score,
            "mental": profile.mental_score,
            "softskill": profile.softskill_score
        }
    }