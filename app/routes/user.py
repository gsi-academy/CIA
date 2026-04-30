from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import date, datetime, timedelta
from typing import Optional, List
import uuid

from app.database import SessionLocal
from app.models.models import (
    Report, ReportAnalysis, ReportParameterDetection, KMSMainIndicator, KMSDetailIndicator,
    KMSProfile, StudentAchievement, Treatment, Student, ReportStatus, Semester
)
from app.core.security import decode_access_token
from app.core.ai_engine import analyze_report
from app.core.tasks import process_ai
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
    # Total students assigned to this musyrif
    total_students = db.query(Student).filter(Student.musyrif_id == user_id).count()
    # Reports submitted by this musyrif this week
    one_week_ago = date.today() - timedelta(days=7)
    reports_this_week = db.query(Report).filter(
        Report.musyrif_id == user_id,
        Report.report_date >= one_week_ago
    ).count()

    # Average KMS scores for all students in this musyrif's domain
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
            "kms_averages": {
                "k": avg_k,
                "m": avg_m,
                "s": avg_s
            }
        },
        "message": "Dashboard stats retrieved successfully"
    }

@router.get("/dashboard/trends", summary="Musyrif Aggregate Trends")
def get_dashboard_trends(timeframe: str = "Bulan", db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    user_role = user.get("role")
    
    # Get all students for this user (or all if admin)
    query = db.query(Student)
    if user_role != 0:
        query = query.filter(Student.musyrif_id == user_id)
    students = query.all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return {"data": [], "message": "Belum ada student"}

    result = []
    today = datetime.utcnow()

    if timeframe == "Semester":
        semesters = db.query(Semester).order_by(Semester.start_date.asc()).all()
        for sem in semesters:
            k_scores, m_scores, s_scores = [], [], []
            for sid in student_ids:
                snapshot = db.query(StudentAnalysisSnapshot).filter(
                    StudentAnalysisSnapshot.student_id == sid,
                    StudentAnalysisSnapshot.semester_id == sem.id
                ).order_by(StudentAnalysisSnapshot.performed_at.desc()).first()
                if snapshot:
                    k_scores.append(snapshot.karakter_score)
                    m_scores.append(snapshot.mental_score)
                    s_scores.append(snapshot.softskill_score)
            
            if k_scores:
                result.append({
                    "label": sem.name,
                    "k": round(sum(k_scores)/len(k_scores), 1),
                    "m": round(sum(m_scores)/len(m_scores), 1),
                    "s": round(sum(s_scores)/len(s_scores), 1)
                })
            else:
                result.append({
                    "label": sem.name,
                    "k": 0.0, "m": 0.0, "s": 0.0
                })
        return {"data": result, "message": "Aggregate trends retrieved successfully"}

    # For other timeframes (Hari, Minggu, Bulan, Tahun)
    points = []
    if timeframe == "Hari":
        points = [(today - timedelta(days=i), (today - timedelta(days=i)).strftime("%d %b")) for i in range(6, -1, -1)]
        points[-1] = (today, "Hari Ini")
    elif timeframe == "Minggu":
        points = [(today - timedelta(weeks=i), f"{i} Mgg Lalu") for i in range(3, 0, -1)]
        points.append((today, "Mgg Ini"))
    elif timeframe == "Bulan":
        points = [(today - timedelta(days=i*30), (today - timedelta(days=i*30)).strftime("%b")) for i in range(5, 0, -1)]
        points.append((today, "Bln Ini"))
    else: # Tahun
        points = [(today - timedelta(days=365), (today - timedelta(days=365)).strftime("%Y")), (today, today.strftime("%Y"))]

    for target_date, label in points:
        k_scores, m_scores, s_scores = [], [], []
        for sid in student_ids:
            snapshot = db.query(StudentAnalysisSnapshot).filter(
                StudentAnalysisSnapshot.student_id == sid,
                StudentAnalysisSnapshot.performed_at <= target_date
            ).order_by(StudentAnalysisSnapshot.performed_at.desc()).first()
            if snapshot:
                k_scores.append(snapshot.karakter_score)
                m_scores.append(snapshot.mental_score)
                s_scores.append(snapshot.softskill_score)
        
        if k_scores:
            result.append({
                "label": label,
                "k": round(sum(k_scores)/len(k_scores), 1),
                "m": round(sum(m_scores)/len(m_scores), 1),
                "s": round(sum(s_scores)/len(s_scores), 1)
            })
        else:
            result.append({
                "label": label,
                "k": 0.0, "m": 0.0, "s": 0.0
            })

    return {
        "data": result,
        "message": "Aggregate trends retrieved successfully"
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
        # Get latest KMS Profile
        profile = db.query(KMSProfile).filter(KMSProfile.student_id == s.id).order_by(KMSProfile.last_updated.desc()).first()
        # Count reports today
        reports_today = db.query(Report).filter(Report.student_id == s.id, Report.report_date == today).count()
        
        student_data = {
            "id": str(s.id),
            "name": s.name,
            "nis": s.nis,
            "kelas": s.kelas,
            "angkatan": s.angkatan,
            "reports_today": reports_today,
            "initials": "".join([n[0] for n in s.name.split() if n]).upper()[:2],
            "role": f"Student {s.kelas}" if s.kelas else "Student",
            "division": s.angkatan if s.angkatan else "N/A",
            "kms": {
                "k": profile.karakter_score if profile else 0,
                "m": profile.mental_score if profile else 0,
                "s": profile.softskill_score if profile else 0
            }
        }
        result.append(student_data)

    return {
        "data": result,
        "message": f"Successfully retrieved {len(result)} students"
    }

@router.get("/students/{id}", summary="Student Detail")
def get_student_detail(id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    user_role = user.get("role")
    
    query = db.query(Student).filter(Student.id == id)
    if user_role != 0:
        query = query.filter(Student.musyrif_id == user_id)
        
    student = query.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau akses ditolak")
    
    # Get latest treatment
    treatment = db.query(Treatment).filter(Treatment.student_id == id).order_by(Treatment.created_at.desc()).first()
    
    # Get latest profile scores
    profile = db.query(KMSProfile).filter(KMSProfile.student_id == id).order_by(KMSProfile.last_updated.desc()).first()

    return {
        "data": {
            "id": str(student.id),
            "name": student.name,
            "nis": student.nis,
            "kelas": student.kelas,
            "angkatan": student.angkatan,
            "birth_info": student.birth_info,
            "address": student.address,
            "guardian_name": student.guardian_name,
            "initials": "".join([n[0] for n in student.name.split() if n]).upper()[:2],
            "role": f"Student {student.kelas}" if student.kelas else "Student",
            "division": student.angkatan if student.angkatan else "N/A",
            "treatment": treatment.recommendation if treatment else "Belum ada analisis mendalam. Silakan jalankan Analisis AI terlebih dahulu.",
            "scores": {
                "k": profile.karakter_score if profile else 0,
                "m": profile.mental_score if profile else 0,
                "s": profile.softskill_score if profile else 0,
                "o": profile.overall_score if profile else 0
            } if profile else None
        },
        "message": "Student detail retrieved successfully"
    }

# =========================
# 2. PERFORMANCE & MASTERS
# =========================

@router.get("/performance/{id}/kms", summary="Student KMS Data")
def get_performance_kms(id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    user_role = user.get("role")
    
    query = db.query(Student).filter(Student.id == id)
    if user_role != 0:
        query = query.filter(Student.musyrif_id == user_id)
        
    student = query.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau akses ditolak")

    # Get all main indicators
    all_params = db.query(KMSMainIndicator).all()
    
    # Get student achievements
    achievements = db.query(StudentAchievement).filter(StudentAchievement.student_id == id).all()
    ach_map = {str(a.parameter_id): a for a in achievements}
    
    result = {"karakter": [], "mental": [], "softskill": []}
    for param in all_params:
        if param.category in result:
            ach = ach_map.get(str(param.id))
            # Include details for dropdown support
            details = []
            for d in param.details:
                details.append({
                    "id": str(d.id),
                    "text": d.indicator_detail
                })
                
            result[param.category].append({
                "id": str(param.id),
                "name": param.name,
                "status": ach.status if ach else "pending",
                "evidence": ach.evidence_excerpt if ach else None,
                "details": details
            })
    return {
        "data": result,
        "message": "KMS performance data retrieved successfully"
    }

@router.get("/performance/{id}/trends", summary="Student Performance Trends")
def get_performance_trends(id: str, timeframe: str = "Semester", db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    user_role = user.get("role")
    
    query = db.query(Student).filter(Student.id == id)
    if user_role != 0:
        query = query.filter(Student.musyrif_id == user_id)
        
    student = query.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau akses ditolak")

    result = []
    today = datetime.utcnow()

    if timeframe == "Semester":
        semesters = db.query(Semester).order_by(Semester.start_date.asc()).all()
        for sem in semesters:
            snapshot = db.query(StudentAnalysisSnapshot).filter(
                StudentAnalysisSnapshot.student_id == id,
                StudentAnalysisSnapshot.semester_id == sem.id
            ).order_by(StudentAnalysisSnapshot.performed_at.desc()).first()
            
            if snapshot:
                result.append({
                    "label": sem.name,
                    "k": round(snapshot.karakter_score, 1),
                    "m": round(snapshot.mental_score, 1),
                    "s": round(snapshot.softskill_score, 1)
                })
            else:
                result.append({
                    "label": sem.name,
                    "k": 0.0,
                    "m": 0.0,
                    "s": 0.0
                })
        return {"data": result}

    # For other timeframes (Hari, Minggu, Bulan, Tahun)
    points = []
    if timeframe == "Hari":
        points = [(today - timedelta(days=i), (today - timedelta(days=i)).strftime("%d %b")) for i in range(6, -1, -1)]
        points[-1] = (today, "Hari Ini")
    elif timeframe == "Minggu":
        points = [(today - timedelta(weeks=i), f"{i} Mgg Lalu") for i in range(3, 0, -1)]
        points.append((today, "Mgg Ini"))
    elif timeframe == "Bulan":
        points = [(today - timedelta(days=i*30), (today - timedelta(days=i*30)).strftime("%b")) for i in range(5, 0, -1)]
        points.append((today, "Bln Ini"))
    else: # Tahun
        points = [(today - timedelta(days=365), (today - timedelta(days=365)).strftime("%Y")), (today, today.strftime("%Y"))]

    for target_date, label in points:
        snapshot = db.query(StudentAnalysisSnapshot).filter(
            StudentAnalysisSnapshot.student_id == id,
            StudentAnalysisSnapshot.performed_at <= target_date
        ).order_by(StudentAnalysisSnapshot.performed_at.desc()).first()
        
        if snapshot:
            result.append({
                "label": label,
                "k": round(snapshot.karakter_score, 1),
                "m": round(snapshot.mental_score, 1),
                "s": round(snapshot.softskill_score, 1)
            })
        else:
            result.append({
                "label": label,
                "k": 0.0,
                "m": 0.0,
                "s": 0.0
            })

    return {
        "data": result,
        "message": f"Performance trends for {timeframe} retrieved successfully"
    }

@router.get("/master/kms-indicators", summary="List KMS Main Indicators with Details")
def get_kms_indicators(db: Session = Depends(get_db), user=Depends(get_current_user)):
    indicators = db.query(KMSMainIndicator).all()
    result = []
    for ind in indicators:
        result.append({
            "id": str(ind.id),
            "category": ind.category,
            "name": ind.name,
            "description": ind.description,
            "theme": ind.theme,
            "weight": ind.weight,
            "details": [{"id": str(d.id), "indicator_detail": d.indicator_detail} for d in ind.details]
        })
    return {
        "data": result,
        "message": "KMS indicators retrieved successfully"
    }

@router.get("/master/semesters", summary="List Semesters")
def get_semesters(db: Session = Depends(get_db), user=Depends(get_current_user)):
    semesters = db.query(Semester).all()
    return {
        "data": semesters,
        "message": "Semesters retrieved successfully"
    }


@router.get("/students/{id}/analyze-latest", summary="Get Latest Analysis Result")
def get_latest_student_analysis(id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    user_role = user.get("role")
    
    query = db.query(Student).filter(Student.id == id)
    if user_role != 0:
        query = query.filter(Student.musyrif_id == user_id)
        
    student = query.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")

    profile = db.query(KMSProfile).filter(KMSProfile.student_id == id).order_by(KMSProfile.last_updated.desc()).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Belum ada data analisis")

    treatment = db.query(Treatment).filter(Treatment.student_id == id, Treatment.semester_id == profile.semester_id).order_by(Treatment.created_at.desc()).first()
    
    # Get achievements for detections
    achievements = db.query(StudentAchievement, KMSMainIndicator).join(
        KMSMainIndicator, StudentAchievement.parameter_id == KMSMainIndicator.id
    ).filter(StudentAchievement.student_id == id, StudentAchievement.status == "achieved").all()
    
    detections = [{"parameter": a[1].name, "category": a[1].category, "status": "achieved"} for a in achievements]

    return {
        "data": {
            "scores": {
                "karakter": profile.karakter_score,
                "mental": profile.mental_score,
                "softskill": profile.softskill_score,
                "overall": profile.overall_score
            },
            "detections": detections,
            "treatment": treatment.recommendation if treatment else "Belum ada rekomendasi",
            "ai_comment": f"Analisis terakhir pada {profile.last_updated.strftime('%d %b %Y')}"
        },
        "message": "Latest analysis retrieved successfully"
    }

# =========================
# 3. REPORTING FLOW
# =========================
@router.post("/reports/submit", summary="Kirim Laporan Saja (Tanpa Analisis)")
def submit_report(
    data: ReportSubmit, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    user_id = user["sub"]
    today = date.today()
    
    # Tangani default semester_id dari frontend
    if data.semester_id == "00000000-0000-0000-0000-000000000000":
        active_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if active_semester:
            data.semester_id = str(active_semester.id)
        else:
            raise HTTPException(status_code=400, detail="Tidak ada semester aktif. Silakan hubungi admin.")

    # Ensure student is assigned to this musyrif
    student = db.query(Student).filter(
        Student.id == uuid.UUID(data.student_id), 
        Student.musyrif_id == uuid.UUID(user_id)
    ).first()
    
    if not student:
        raise HTTPException(status_code=403, detail="Anda tidak diizinkan membuat laporan untuk student ini")

    # Langsung status pending
    report = Report(
        musyrif_id=uuid.UUID(user_id),
        student_id=uuid.UUID(data.student_id),
        semester_id=uuid.UUID(data.semester_id),
        report_date=today,
        transcript=data.transcript,
        status=ReportStatus.pending
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "data": {"report_id": str(report.id), "status": "pending"},
        "message": "Laporan disimpan tanpa analisis"
    }


@router.post("/reports/analyze", summary="Kirim Laporan dan Analisis")
def analyze_report_endpoint(
    data: ReportSubmit, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    user_id = user["sub"]
    today = date.today()

    # Tangani default semester_id dari frontend
    if data.semester_id == "00000000-0000-0000-0000-000000000000":
        active_semester = db.query(Semester).filter(Semester.is_active == True).first()
        if active_semester:
            data.semester_id = str(active_semester.id)
        else:
            raise HTTPException(status_code=400, detail="Tidak ada semester aktif. Silakan hubungi admin.")

    student = db.query(Student).filter(
        Student.id == uuid.UUID(data.student_id), 
        Student.musyrif_id == uuid.UUID(user_id)
    ).first()

    if not student:
        raise HTTPException(status_code=403, detail="Anda tidak diizinkan membuat laporan untuk student ini")

    report = Report(
        musyrif_id=uuid.UUID(user_id),
        student_id=uuid.UUID(data.student_id),
        semester_id=uuid.UUID(data.semester_id),
        report_date=today,
        transcript=data.transcript,
        status=ReportStatus.pending
    )
    db.add(report)
    db.commit()

    analysis_result = run_analysis_for_student(
        student_id=data.student_id,
        semester_id=data.semester_id,
        performer_id=user_id,
        db=db
    )

    if "error" in analysis_result:
        raise HTTPException(status_code=400, detail=analysis_result["error"])

    return {
        "data": {
            "report_id": str(report.id),
            "status": "Submited",
            **analysis_result
        },
        "message": "Laporan disimpan dan analisis kumulatif selesai"
    }


@router.get("/reports/{report_id}")
def get_report_status(report_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    report = db.query(Report).filter(Report.id == report_id, Report.musyrif_id == user_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")
    
    analysis = db.query(ReportAnalysis).filter(ReportAnalysis.report_id == report.id).first()
    detections = []
    if analysis:
        raw_detections = db.query(ReportParameterDetection, KMSDetailIndicator).join(
            KMSDetailIndicator, ReportParameterDetection.detail_parameter_id == KMSDetailIndicator.id
        ).filter(ReportParameterDetection.report_analysis_id == analysis.id).all()
        detections = [{"parameter": rd[1].indicator_detail, "status": rd[0].status_detected} for rd in raw_detections]
        
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
@router.get("/history/{student_id}")
def get_student_history(student_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    student = db.query(Student).filter(Student.id == student_id, Student.musyrif_id == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau bukan bimbingan Anda")

    reports = db.query(Report).filter(Report.student_id == student_id).order_by(desc(Report.report_date)).all()
    return {
        "data": [{"id": str(r.id), "date": r.report_date, "status": r.status} for r in reports],
        "message": "Student history retrieved successfully"
    }

@router.get("/export/rapor/{student_id}")
def export_rapor(student_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    user_id = user["sub"]
    student = db.query(Student).filter(Student.id == student_id, Student.musyrif_id == user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau bukan bimbingan Anda")
        
    profile = db.query(KMSProfile).filter(KMSProfile.student_id == student_id).order_by(KMSProfile.last_updated.desc()).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Data performa belum tersedia")
    
    return {
        "data": {
            "student_name": student.name,
            "overall_score": profile.overall_score,
            "report_count": profile.report_count,
            "status": "Ready for PDF generation"
        },
        "message": "Report exported successfully"
    }


# =========================
# 5. ANALISIS KUMULATIF
# =========================
from app.services.analysis_service import run_analysis_for_student, format_full_snapshot
from app.models.models import StudentAnalysisSnapshot

@router.post("/analyze/student/{student_id}", summary="Jalankan Analisis Kumulatif untuk 1 Student")
def analyze_student(
    student_id: str,
    semester_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    user_id = user["sub"]
    user_role = user.get("role")

    query = db.query(Student).filter(Student.id == student_id)
    if user_role != 0:
        query = query.filter(Student.musyrif_id == user_id)

    student = query.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau akses ditolak")

    result = run_analysis_for_student(student_id, semester_id, user_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "data": result,
        "message": f"Analisis kumulatif untuk {student.name} berhasil dijalankan."
    }


@router.post("/analyze/domain", summary="Jalankan Analisis Kumulatif untuk Seluruh Domain Musyrif")
def analyze_domain(
    semester_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    user_id = user["sub"]
    students = db.query(Student).filter(Student.musyrif_id == user_id, Student.is_active == True).all()
    if not students:
        raise HTTPException(status_code=404, detail="Tidak ada student aktif dalam domain Anda")

    results = []
    errors = []
    for student in students:
        try:
            res = run_analysis_for_student(str(student.id), semester_id, user_id, db)
            if "error" in res:
                errors.append({"student_id": str(student.id), "name": student.name, "error": res["error"]})
            else:
                results.append({"student_id": str(student.id), "name": student.name, "snapshot_id": res["snapshot_id"]})
        except Exception as e:
            errors.append({"student_id": str(student.id), "name": student.name, "error": str(e)})

    return {
        "data": {
            "processed": len(results),
            "skipped": len(errors),
            "results": results,
            "errors": errors
        },
        "message": f"Analisis domain selesai: {len(results)} berhasil, {len(errors)} dilewati."
    }


# =========================
# 6. HISTORY LAPORAN
# =========================
@router.get("/history/reports/{student_id}", summary="History Laporan Student dengan Filter & Paginasi")
def get_report_history(
    student_id: str,
    semester_id: Optional[str] = None,
    from_date: Optional[str] = None,   # format: YYYY-MM-DD
    to_date: Optional[str] = None,     # format: YYYY-MM-DD
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    from datetime import date as date_type
    user_id = user["sub"]
    user_role = user.get("role")

    # Verifikasi akses
    query_s = db.query(Student).filter(Student.id == student_id)
    if user_role != 0:
        query_s = query_s.filter(Student.musyrif_id == user_id)
    student = query_s.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau akses ditolak")

    # Build query laporan
    query = db.query(Report).filter(Report.student_id == student_id)
    if semester_id:
        query = query.filter(Report.semester_id == semester_id)
    if from_date:
        query = query.filter(Report.report_date >= date_type.fromisoformat(from_date))
    if to_date:
        query = query.filter(Report.report_date <= date_type.fromisoformat(to_date))

    total = query.count()
    reports = query.order_by(desc(Report.report_date)).offset((page - 1) * size).limit(size).all()

    items = []
    for r in reports:
        items.append({
            "id": str(r.id),
            "date": r.report_date.isoformat() if r.report_date else None,
            "status": r.status,
            "transcript": r.transcript,
            "semester_id": str(r.semester_id) if r.semester_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return {
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": (total + size - 1) // size
            }
        },
        "message": f"History laporan untuk {student.name} berhasil diambil."
    }


# =========================
# 7. HISTORY ANALISIS
# =========================
@router.get("/history/analysis/{student_id}", summary="Daftar Semua Snapshot Analisis Student")
def get_analysis_history(
    student_id: str,
    semester_id: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    user_id = user["sub"]
    user_role = user.get("role")

    query_s = db.query(Student).filter(Student.id == student_id)
    if user_role != 0:
        query_s = query_s.filter(Student.musyrif_id == user_id)
    student = query_s.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau akses ditolak")

    query = db.query(StudentAnalysisSnapshot).filter(StudentAnalysisSnapshot.student_id == student_id)
    if semester_id:
        query = query.filter(StudentAnalysisSnapshot.semester_id == semester_id)

    total = query.count()
    snapshots = query.order_by(StudentAnalysisSnapshot.performed_at.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for snap in snapshots:
        items.append({
            "snapshot_id": str(snap.id),
            "performed_at": snap.performed_at.isoformat(),
            "semester_id": str(snap.semester_id),
            "reports_included": snap.reports_included,
            "scores": {
                "karakter": snap.karakter_score,
                "mental": snap.mental_score,
                "softskill": snap.softskill_score,
                "overall": snap.overall_score
            }
        })

    return {
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": (total + size - 1) // size
            }
        },
        "message": "Daftar snapshot analisis berhasil diambil."
    }


@router.get("/history/analysis/{student_id}/{snapshot_id}", summary="Detail Lengkap 1 Snapshot Analisis")
def get_analysis_snapshot_detail(
    student_id: str,
    snapshot_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    user_id = user["sub"]
    user_role = user.get("role")

    query_s = db.query(Student).filter(Student.id == student_id)
    if user_role != 0:
        query_s = query_s.filter(Student.musyrif_id == user_id)
    student = query_s.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan atau akses ditolak")

    snapshot = db.query(StudentAnalysisSnapshot).filter(
        StudentAnalysisSnapshot.id == snapshot_id,
        StudentAnalysisSnapshot.student_id == student_id
    ).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot analisis tidak ditemukan")

    return {
        "data": format_full_snapshot(snapshot, db),
        "message": "Detail snapshot berhasil diambil."
    }

