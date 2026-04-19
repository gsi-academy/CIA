from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.models import (
    Report,
    ReportVariableScore,
    ReportAnalysis,
    Treatment
)
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/history", tags=["History"])

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
# AUTH JWT
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


# =========================
# HISTORY SANTRI
# =========================
@router.get("/santri/{santri_id}")
def get_history(
    santri_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    reports = db.query(Report).filter(
        Report.santri_id == santri_id
    ).order_by(desc(Report.report_date)).all()

    result = []

    for report in reports:

        # =========================
        # AI SCORES
        # =========================
        scores = db.query(ReportVariableScore).join(
            ReportAnalysis,
            ReportVariableScore.report_analysis_id == ReportAnalysis.id
        ).filter(
            ReportAnalysis.report_id == report.id
        ).all()

        score_data = {
            "character": None,
            "mental": None,
            "softskill": None
        }

        for s in scores:
            score_data["character"] = s.score  # simplifikasi
            score_data["mental"] = s.score
            score_data["softskill"] = s.score

        # =========================
        # TREATMENT
        # =========================
        treatments = db.query(Treatment).filter(
            Treatment.generated_from_report == report.id
        ).all()

        treatment_list = [
            {
                "recommendation": t.recommendation,
                "priority": t.priority
            }
            for t in treatments
        ]

        result.append({
            "report_id": str(report.id),
            "date": report.report_date,
            "status": report.status,
            "transcript": report.transcript,
            "ai_score": score_data,
            "treatments": treatment_list
        })

    return {
        "santri_id": santri_id,
        "history": result
    }