from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date, datetime
from typing import Optional, List

from app.database import SessionLocal
from app.models.models import (
    Report, ReportAnalysis, ReportParameterDetection, KMSParameter,
    KMSProfile, StudentAchievement, Treatment, Student, ReportStatus, Semester
)
from app.core.security import decode_access_token
from app.core.ai_engine import analyze_report
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(tags=["User Panel (Musyrif)"])

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
# AUTH MIDDLEWARE
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

from app.schemas.report import ReportSubmit, ReportVerify

# =========================
# 1. DASHBOARD & STUDENTS
# =========================

@router.get("/dashboard/stats", summary="Musyrif Dashboard Stats")
def get_dashboard_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    # Total students assigned (for now just total students)
    total_students = db.query(Student).count()
    # Reports submitted by this musyrif this week
    from datetime import timedelta
    one_week_ago = date.today() - timedelta(days=7)
    reports_this_week = db.query(Report).filter(
        Report.musyrif_id == user_id,
        Report.report_date >= one_week_ago
    ).count()

    return {
        "data": {
            "total_students": total_students,
            "reports_this_week": reports_this_week
        },
        "message": "Dashboard stats retrieved successfully"
    }

@router.get("/students", summary="List Students")
def get_students(search: Optional[str] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(Student)
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))
    students = query.all()
    return {
        "data": students,
        "message": f"Successfully retrieved {len(students)} students"
    }

@router.get("/students/{id}", summary="Student Detail")
def get_student_detail(id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Santri tidak ditemukan")
    
    return {
        "data": student,
        "message": "Student detail retrieved successfully"
    }

# =========================
# 2. PERFORMANCE & MASTERS
# =========================

@router.get("/performance/{id}/kms", summary="Student KMS Data")
def get_performance_kms(id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    achievements = db.query(StudentAchievement, KMSParameter).join(
        KMSParameter, StudentAchievement.parameter_id == KMSParameter.id
    ).filter(StudentAchievement.santri_id == id).all()
    
    result = {"karakter": [], "mental": [], "softskill": []}
    for ach, param in achievements:
        result[param.category].append({
            "name": param.name,
            "status": ach.status,
            "evidence": ach.evidence_excerpt
        })
    return {
        "data": result,
        "message": "KMS performance data retrieved successfully"
    }

@router.get("/performance/{id}/trends", summary="Student Performance Trends")
def get_performance_trends(id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Mocking trend data for now
    # In a real app, this would aggregate scores over time from KMSProfile or Reports
    trends = [
        {"month": "Jan", "score": 75},
        {"month": "Feb", "score": 80},
        {"month": "Mar", "score": 78},
        {"month": "Apr", "score": 85},
    ]
    return {
        "data": trends,
        "message": "Performance trends retrieved successfully"
    }

@router.get("/master/kms-params", summary="List KMS Parameters")
def get_kms_params(db: Session = Depends(get_db), user=Depends(get_current_user)):
    params = db.query(KMSParameter).all()
    return {
        "data": params,
        "message": "KMS parameters retrieved successfully"
    }

# =========================
# 3. REPORTING FLOW
# =========================
@router.post("/reports/submit")
def submit_report(data: ReportSubmit, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    today = date.today()
    
    # 1 Hari 1 Laporan per Santri per Musyrif
    existing = db.query(Report).filter(
        Report.musyrif_id == user_id,
        Report.santri_id == data.santri_id,
        Report.report_date == today
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Laporan sudah dikirim hari ini")
    
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
        "data": {"report_id": str(report.id)},
        "message": "Laporan berhasil disimpan"
    }

@router.post("/reports/analyze", summary="Analyze Voice-to-Text")
def analyze_voice_report(data: ReportVerify, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # This simulates the AI analysis of voice-to-text input
    if not data.text or len(data.text) < 10:
        raise HTTPException(status_code=400, detail="Teks terlalu pendek untuk dianalisis")
    
    # Mocking AI result for immediate feedback
    # In a real app, this might call analyze_report synchronously or return a taskId
    analysis_mock = {
        "insight": "Santri menunjukkan kemajuan dalam kedisiplinan.",
        "detections": [
            {"parameter": "Shalat Berjamaah", "status": "gained", "evidence": "Hadir tepat waktu"},
            {"parameter": "Adab Makan", "status": "gained", "evidence": "Makan dengan tangan kanan"}
        ]
    }
    return {
        "data": analysis_mock,
        "message": "Analysis completed successfully"
    }

@router.put("/reports/{report_id}/verify")
def verify_report(
    report_id: str, 
    data: ReportVerify, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.status != ReportStatus.pending:
        raise HTTPException(status_code=400, detail="Laporan tidak valid untuk verifikasi")
    
    if data.text:
        report.transcript = data.text
    
    report.status = ReportStatus.processing
    db.commit()
    
    from app.core.tasks import process_ai # Corrected path
    background_tasks.add_task(process_ai, str(report.id))
    
    return {
        "data": {"status": "processing"},
        "message": "Sedang dianalisis AI"
    }

@router.get("/reports/{report_id}")
def get_report_status(report_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    
    analysis = db.query(ReportAnalysis).filter(ReportAnalysis.report_id == report.id).first()
    detections = []
    if analysis:
        raw_detections = db.query(ReportParameterDetection, KMSParameter).join(
            KMSParameter, ReportParameterDetection.parameter_id == KMSParameter.id
        ).filter(ReportParameterDetection.report_analysis_id == analysis.id).all()
        detections = [{"parameter": rd[1].name, "category": rd[1].category, "status": rd[0].status_detected} for rd in raw_detections]
        
    return {
        "data": {
            "status": report.status,
            "transcript": report.transcript,
            "analysis": {
                "insight": analysis.insight if analysis else None,
                "detections": detections
            } if analysis else None
        },
        "message": "Report status retrieved successfully"
    }

# =========================
# 4. HISTORY & EXPORT
# =========================
@router.get("/history/{santri_id}")
def get_student_history(santri_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    reports = db.query(Report).filter(Report.santri_id == santri_id).order_by(desc(Report.report_date)).all()
    return {
        "data": [{"id": str(r.id), "date": r.report_date, "status": r.status} for r in reports],
        "message": "Student history retrieved successfully"
    }

@router.get("/export/rapor/{santri_id}")
def export_rapor(santri_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    santri = db.query(Student).filter(Student.id == santri_id).first()
    profile = db.query(KMSProfile).filter(KMSProfile.santri_id == santri_id).first()
    if not santri or not profile:
        raise HTTPException(status_code=404, detail="Data tidak lengkap")
    
    return {
        "data": {
            "santri_name": santri.name,
            "overall_score": profile.overall_score,
            "report_count": profile.report_count,
            "status": "Ready for PDF generation"
        },
        "message": "Report exported successfully"
    }
