from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import date, datetime, timedelta
from typing import Optional, List
import uuid

from app.database import SessionLocal
from app.models.models import (
    Report, ReportAnalysis, ReportParameterDetection, KMSMainIndicator, KMSDetailIndicator,
    KMSProfile, StudentAchievement, Treatment, Student, ReportStatus, Semester, 
    StudentGrade, StudentAnalysisSnapshot  # Pastiin StudentGrade ada di models.py lu
)
from app.core.security import decode_access_token
from app.core.ai_engine import analyze_report
from app.core.tasks import process_ai
from fastapi.security import OAuth2PasswordBearer
from app.schemas.report import ReportSubmit, ReportVerify
from app.services.analysis_service import run_analysis_for_student, format_full_snapshot

router = APIRouter(tags=["User Panel (Musyrif)"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# =========================
# DB SESSION & AUTH
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

# =========================
# 1. DASHBOARD & STUDENTS
# =========================

@router.get("/dashboard/stats", summary="Musyrif Dashboard Stats")
def get_dashboard_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    total_students = db.query(Student).filter(Student.musyrif_id == user_id).count()
    
    one_week_ago = date.today() - timedelta(days=7)
    reports_this_week = db.query(Report).filter(
        Report.musyrif_id == user_id,
        Report.report_date >= one_week_ago
    ).count()

    profiles = db.query(KMSProfile).join(
        Student, KMSProfile.student_id == Student.id
    ).filter(Student.musyrif_id == user_id).all()
    
    if profiles:
        avg_k = round(sum(p.karakter_score for p in profiles) / len(profiles), 1)
        avg_m = round(sum(p.mental_score for p in profiles) / len(profiles), 1)
        avg_s = round(sum(p.softskill_score for p in profiles) / len(profiles), 1)
    else:
        avg_k = avg_m = avg_s = 0

    return {
        "data": {
            "total_students": total_students,
            "reports_this_week": reports_this_week,
            "kms_averages": {"k": avg_k, "m": avg_m, "s": avg_s}
        },
        "message": "Dashboard stats retrieved successfully"
    }

@router.get("/students", summary="List Students")
def get_students(search: Optional[str] = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    query = db.query(Student).filter(Student.musyrif_id == user_id)
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))
    students = query.all()
    
    result = []
    today = date.today()
    for s in students:
        profile = db.query(KMSProfile).filter(KMSProfile.student_id == s.id).order_by(KMSProfile.last_updated.desc()).first()
        reports_today = db.query(Report).filter(Report.student_id == s.id, Report.report_date == today).count()
        
        result.append({
            "id": str(s.id),
            "name": s.name,
            "nis": s.nis,
            "kelas": s.kelas,
            "angkatan": s.angkatan,
            "reports_today": reports_today,
            "kms": {
                "k": profile.karakter_score if profile else 0,
                "m": profile.mental_score if profile else 0,
                "s": profile.softskill_score if profile else 0
            }
        })
    return {"data": result, "message": "Success"}

@router.get("/students/{student_id}", summary="Student Detail")
def get_student_detail(student_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    student = db.query(Student).filter(Student.id == student_id, Student.musyrif_id == user_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")
    
    treatment = db.query(Treatment).filter(Treatment.student_id == student_id).order_by(Treatment.created_at.desc()).first()
    profile = db.query(KMSProfile).filter(KMSProfile.student_id == student_id).order_by(KMSProfile.last_updated.desc()).first()

    return {
        "data": {
            "id": str(student.id),
            "name": student.name,
            "nis": student.nis,
            "treatment": treatment.recommendation if treatment else "Belum ada analisis.",
            "scores": {
                "k": profile.karakter_score if profile else 0,
                "m": profile.mental_score if profile else 0,
                "s": profile.softskill_score if profile else 0,
                "o": profile.overall_score if profile else 0
            } if profile else None
        }
    }

@router.get("/students/{student_id}/grades", summary="Musyrif: Get Student Grades")
def get_student_grades_musyrif(student_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Verifikasi hak akses musyrif
    student = db.query(Student).filter(Student.id == student_id, Student.musyrif_id == current_user["sub"]).first()
    if not student:
        raise HTTPException(status_code=403, detail="Akses ditolak.")

    # Pake StudentGrade sesuai model yang lu punya
    grades = db.query(StudentGrade, Semester).join(
        Semester, StudentGrade.semester_id == Semester.id
    ).filter(StudentGrade.student_id == student_id).all()
    
    return {
        "status": "success",
        "data": [
            {
                "semester_name": sem.name,
                "nh": g.nh,
                "nb": g.nb,
                "na": g.na
            } for g, sem in grades
        ]
    }

# =========================
# 2. REPORTING FLOW
# =========================

@router.post("/reports/submit", summary="Kirim Laporan")
def submit_report(data: ReportSubmit, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    
    # Cek Semester Aktif jika ID kosong
    if data.semester_id == "00000000-0000-0000-0000-000000000000":
        sem = db.query(Semester).filter(Semester.is_active == True).first()
        if not sem: raise HTTPException(status_code=400, detail="No active semester")
        data.semester_id = str(sem.id)

    report = Report(
        musyrif_id=uuid.UUID(user_id),
        student_id=uuid.UUID(data.student_id),
        semester_id=uuid.UUID(data.semester_id),
        report_date=date.today(),
        transcript=data.transcript,
        status=ReportStatus.pending
    )
    db.add(report)
    db.commit()
    return {"data": {"report_id": str(report.id)}, "message": "Laporan disimpan"}

# =========================
# 3. HISTORY ANALISIS
# =========================

@router.get("/history/analysis/{student_id}", summary="Daftar Snapshot Analisis")
def get_analysis_history(student_id: str, page: int = 1, size: int = 10, db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(StudentAnalysisSnapshot).filter(StudentAnalysisSnapshot.student_id == student_id)
    total = query.count()
    snapshots = query.order_by(StudentAnalysisSnapshot.performed_at.desc()).offset((page - 1) * size).limit(size).all()

    return {
        "data": {
            "items": [
                {
                    "snapshot_id": str(snap.id),
                    "performed_at": snap.performed_at.isoformat(),
                    "scores": {"k": snap.karakter_score, "m": snap.mental_score, "s": snap.softskill_score}
                } for snap in snapshots
            ],
            "total": total
        }
    }