from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel
from typing import Optional

from app.database import SessionLocal
from app.models.models import Report, ReportStatus, ReportAnalysis, ReportVariableScore
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

from app.models.models import Treatment

# Import AI Engine (Pastikan file app/core/ai_engine.py sudah dibuat)
from app.core.ai_engine import analyze_report

router = APIRouter(prefix="/reports", tags=["Reports"])

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
# AUTH (JWT)
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload  # {sub: user_id, role: 0/1}


# =========================
# REQUEST SCHEMA
# =========================
class ReportSubmit(BaseModel):
    santri_id: str
    semester_id: str
    transcript: str


class ReportVerify(BaseModel):
    text: Optional[str] = None


# =========================
# 1. SUBMIT LAPORAN (TEXT)
# =========================
@router.post("/submit")
def submit_report(
    data: ReportSubmit,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["sub"]
    today = date.today()

    # =========================
    # RULE: 1 HARI 1 LAPORAN
    # =========================
    existing = db.query(Report).filter(
        Report.musyrif_id == user_id,
        Report.santri_id == data.santri_id,
        Report.report_date == today
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Laporan untuk santri ini sudah ada hari ini"
        )

    # =========================
    # SIMPAN KE DATABASE
    # =========================
    report = Report(
        musyrif_id=user_id,
        santri_id=data.santri_id,
        semester_id=data.semester_id,
        report_date=today,
        audio_url=None,  # tidak dipakai lagi
        transcript=data.transcript,
        status=ReportStatus.pending
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Laporan berhasil dikirim",
        "report_id": str(report.id)
    }


# =========================
# 2. VERIFIKASI LAPORAN
# =========================
@router.put("/{report_id}/verify")
def verify_report(
    report_id: str,
    data: ReportVerify,
    background_tasks: BackgroundTasks,  # <--- DITAMBAHKAN DI SINI
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")

    if report.status != ReportStatus.pending:
        raise HTTPException(status_code=400, detail="Report sudah diproses")

    # update transcript jika diedit
    if data.text:
        report.transcript = data.text

    # ubah status
    report.status = ReportStatus.processing
    db.commit()

    # =========================
    # AI PROCESS DI BACKGROUND
    # =========================
    background_tasks.add_task(process_ai, str(report.id))

    return {
        "message": "Laporan diverifikasi dan dikirim ke AI Engine untuk diproses"
    }


# =========================
# 3. FUNCTION AI PROCESS (BACKGROUND)
# =========================
def process_ai(report_id: str):
    db = SessionLocal()

    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        db.close()
        return

    try:
        # =========================
        # JALANKAN AI
        # =========================
        result = analyze_report(report.transcript)

        # =========================
        # SIMPAN ANALYSIS
        # =========================
        analysis = ReportAnalysis(
            report_id=report.id,
            raw_llm_output=result,
            model_used="gpt-4o-mini",
            processing_ms=0
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # =========================
        # SIMPAN SCORE DETAIL
        # =========================
        scores = [
            ("karakter", result.get("karakter_score", 0)),
            ("mental", result.get("mental_score", 0)),
            ("softskill", result.get("softskill_score", 0)),
        ]

        for dim, score in scores:
            db.add(ReportVariableScore(
                report_analysis_id=analysis.id,
                santri_id=report.santri_id,
                kms_variable_id=None,  # sementara kosong (nanti kita mapping KMS)
                score=score,
                evidence_excerpt=report.transcript,
                sentiment="neutral"
            ))

        # Ubah status laporan jadi 'analyzed' setelah sukses
        report.status = ReportStatus.analyzed
        db.commit()

    except Exception as e:
        print(f"Error saat memproses AI: {e}")
        report.status = ReportStatus.failed
        db.commit()

        # =========================
        # SIMPAN TREATMENT
        # =========================
        db.add(Treatment(
            santri_id=report.santri_id,
            semester_id=report.semester_id,
            generated_from_report=report.id,
            recommendation=result.get("recommendation"),
            priority="medium",
            status="pending"
        ))
        db.commit()
    
    finally:
        db.close()
