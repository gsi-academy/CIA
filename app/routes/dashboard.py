from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import SessionLocal
from app.models.models_v2 import (
    Report,
    ReportAnalysis,
    StudentChar,
    StudentMental,
    StudentSoftskill
)
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

from app.core.alerts import check_and_alert
from app.schemas.report import DashboardResponse
from app.models.models_v2 import Student

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
# ... (import tetap sama)

@router.get(
    "/santri/{santri_id}",
    response_model=DashboardResponse,
    summary="Dashboard Santri",
    description="Mengambil ringkasan performa santri berdasarkan hasil analisis AI."
)
def get_santri_dashboard(
    santri_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    all_scores = db.query(ReportVariableScore).filter(
        ReportVariableScore.santri_id == santri_id
    ).order_by(desc(ReportVariableScore.id)).all()

    # FIX: Pakai HTTPException supaya validasi response_model tidak error
    if not all_scores:
        raise HTTPException(
            status_code=404, 
            detail="Belum ada data AI untuk santri ini. Pastikan laporan sudah di-verify."
        )

    total = len(all_scores)
    avg = sum([s.score for s in all_scores]) / total

    # (Logika Trend & KMS Profile tetap sama ...)
    if total < 2:
        trend = "stable"
    else:
        latest_score = all_scores[0].score
        previous_avg = sum([s.score for s in all_scores[1:]]) / (total - 1)
        if latest_score > previous_avg + 5:
            trend = "improving"
        elif latest_score < previous_avg - 5:
            trend = "declining"
        else:
            trend = "stable"

    profile = db.query(KMSProfile).filter(KMSProfile.santri_id == santri_id).first()
    if not profile:
        profile = KMSProfile(
            santri_id=santri_id, karakter_score=avg, mental_score=avg,
            softskill_score=avg, overall_score=avg, report_count=total
        )
        db.add(profile)
    else:
        profile.karakter_score = avg
        profile.mental_score = avg
        profile.softskill_score = avg
        profile.overall_score = avg
        profile.report_count = total
    db.commit()

    santri = db.query(Santri).filter(Santri.id == santri_id).first()
    alert_message = check_and_alert(santri.name if santri else "Unknown", trend, avg)

    return {
        "santri_id": santri_id,
        "total_reports": total,
        "average_score": avg,
        "trend": trend,
        "alert": alert_message,
        # "status": "dashboard updated" # Hapus ini jika tidak ada di DashboardResponse schema
    }