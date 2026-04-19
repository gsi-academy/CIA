from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models.models import (
    ReportVariableScore,
    KMSProfile
)
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
    return payload


# =========================
# DASHBOARD SANTRI
# =========================
@router.get("/santri/{santri_id}")
def get_santri_dashboard(
    santri_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    # =========================
    # AMBIL RATA-RATA SCORE
    # =========================
    scores = db.query(
        func.avg(ReportVariableScore.score).label("avg_score")
    ).filter(
        ReportVariableScore.santri_id == santri_id
    ).all()

    # karena belum mapping KMS variable detail, kita simplify:
    all_scores = db.query(ReportVariableScore).filter(
        ReportVariableScore.santri_id == santri_id
    ).all()

    if not all_scores:
        return {
            "message": "Belum ada data AI untuk santri ini"
        }

    total = len(all_scores)
    avg = sum([s.score for s in all_scores]) / total

    # =========================
    # UPDATE / UPSERT KMS PROFILE
    # =========================
    profile = db.query(KMSProfile).filter(
        KMSProfile.santri_id == santri_id
    ).first()

    if not profile:
        profile = KMSProfile(
            santri_id=santri_id,
            karakter_score=avg,
            mental_score=avg,
            softskill_score=avg,
            overall_score=avg,
            report_count=total
        )
        db.add(profile)
    else:
        profile.karakter_score = avg
        profile.mental_score = avg
        profile.softskill_score = avg
        profile.overall_score = avg
        profile.report_count = total

    db.commit()

    return {
        "santri_id": santri_id,
        "total_reports": total,
        "average_score": avg,
        "status": "dashboard updated"
    }