from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas.report import ExportResponse
from app.models.models import (
    ReportVariableScore,
    Treatment,
    Santri
)
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/export", tags=["Export"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =========================
# DB
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
    return decode_access_token(token)


# =========================
# EXPORT RAPOR
# =========================
@router.get(
    "/rapor/{santri_id}",
    response_model=ExportResponse,
    summary="Export Rapor Santri",
    description="Mengambil data ringkasan performa santri untuk kebutuhan rapor digital."
)
def export_rapor(
    santri_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    santri = db.query(Santri).filter(Santri.id == santri_id).first()
    
    # FIX: Cek dulu santrinya ada atau nggak
    if not santri:
        raise HTTPException(status_code=404, detail="Santri tidak ditemukan")

    scores = db.query(ReportVariableScore).filter(
        ReportVariableScore.santri_id == santri_id
    ).all()

    # FIX: Pakai HTTPException agar tidak kena ResponseValidationError
    if not scores:
        raise HTTPException(
            status_code=404, 
            detail="Belum ada data nilai untuk rapor santri ini."
        )

    total = len(scores)
    avg = sum([s.score for s in scores]) / total

    treatments = db.query(Treatment).filter(
        Treatment.santri_id == santri_id
    ).all()

    treatment_list = [
        {
            "recommendation": t.recommendation,
            "priority": t.priority,
            "status": t.status
        }
        for t in treatments
    ]

    return {
        "santri": {
            "id": santri_id,
            "name": santri.name
        },
        "summary": {
            "average_score": avg,
            "total_reports": total
        },
        "treatments": treatment_list
    }