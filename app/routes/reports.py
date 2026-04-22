from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel
from typing import Optional

from app.database import SessionLocal
from app.models.models_v2 import (
    Report,
    ReportAnalysis,
    ReportCharStatus,
    ReportMentalStatus,
    ReportSoftskillStatus
)
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

# Import AI Engine
from app.schemas.report import ReportResponse, ReportSubmit
from app.core.ai_engine import analyze_report

router = APIRouter(prefix="/reports", tags=["Reports"])

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
# AUTH (JWT)
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


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
@router.post(
    "/submit",
    response_model=ReportResponse,
    summary="Submit Laporan Santri",
    description="Menerima transkrip laporan harian musyrif untuk dianalisis oleh AI."
)
def submit_report(
    data: ReportSubmit,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["sub"]
    today = date.today()

    # Rule: 1 Hari 1 Laporan (Bisa dimatikan sementara dengan comment untuk testing)
    existing = db.query(Report).filter(
        Report.musyrif_id == user_id,
        Report.santri_id == data.santri_id,
        Report.report_date == today
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Laporan untuk santri ini sudah ada hari ini")

    report = Report(
        musyrif_id=user_id,
        santri_id=data.santri_id,
        semester_id=data.semester_id,
        report_date=today,
        transcript=data.transcript,
        status=ReportStatus.pending
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Laporan berhasil dikirim",
        "report_id": str(report.id)  # <--- INI YANG PENTING!
    }

# =========================
# 2. VERIFIKASI LAPORAN
# =========================
@router.put("/{report_id}/verify")
def verify_report(
    report_id: str,
    data: ReportVerify,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")
    if report.status != ReportStatus.pending:
        raise HTTPException(status_code=400, detail="Report sudah diproses")

    if data.text:
        report.transcript = data.text

    report.status = ReportStatus.processing
    db.commit()

    background_tasks.add_task(process_ai, str(report.id))
    return {"message": "Laporan diverifikasi dan dikirim ke AI Engine"}


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
        # 1. Jalankan AI (Sekarang outputnya ada 'evidence')
        result = analyze_report(report.transcript)

        # 2. Simpan Analysis
        analysis = ReportAnalysis(
            report_id=report.id,
            raw_llm_output=result,
            model_used="gpt-4o-mini",
            processing_ms=0
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # ========================================================
        # UPDATE DI SINI: SIMPAN SCORE DETAIL + EVIDENCE (KMS MAPPING)
        # ========================================================
        scores = [
            ("karakter", result["karakter_score"], result["evidence"].get("karakter")),
            ("mental", result["mental_score"], result["evidence"].get("mental")),
            ("softskill", result["softskill_score"], result["evidence"].get("softskill")),
        ]

        for dim, score, evidence in scores:
            db.add(ReportVariableScore(
                report_analysis_id=analysis.id,
                santri_id=report.santri_id,
                kms_variable_id=None,
                score=score,
                evidence_excerpt=evidence,  # <--- BUKTI TEKS AI MASUK KE SINI
                sentiment="neutral"
            ))

        # 3. SIMPAN TREATMENT
        db.add(Treatment(
            santri_id=report.santri_id,
            semester_id=report.semester_id,
            generated_from_report=report.id,
            recommendation=result.get("recommendation", "Pantau terus perkembangan santri."),
            priority="medium",
            status="pending"
        ))

        # 4. Update Status Laporan
        report.status = ReportStatus.analyzed
        db.commit()

    except Exception as e:
        print(f"Error saat memproses AI: {e}")
        report.status = ReportStatus.failed
        db.commit()
    finally:
        db.close()