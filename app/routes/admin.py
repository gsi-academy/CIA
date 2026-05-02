from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
import uuid
import json

from typing import List

from app.database import SessionLocal
from app.models.models import (
    User, Student, Semester, KMSMainIndicator, KMSDetailIndicator, Report, KMSProfile, ReportAnalysis, StudentAchievement, ReportParameterDetection, ActivityLog, StudentAnalysisSnapshot,
    AcademicClass, ClassStudent, StudentGrade
)
from sqlalchemy.dialects.postgresql import insert
from app.core.security import decode_access_token, hash_password
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

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
def get_current_admin(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != 0:
        raise HTTPException(status_code=403, detail="Akses khusus Admin")
    return payload

from app.schemas.auth import MusyrifCreate, UserResponse
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.schemas.semester import SemesterCreate, SemesterResponse, AcademicClassCreate, AcademicClassResponse
from app.schemas.kms import KMSIndicatorCreate, KMSIndicatorResponse, KMSDetailCreate

# ================= SCHEMA =================

class GradeItem(BaseModel):
    studentId: uuid.UUID
    nh: float
    nb: float
    na: float


class GradePayload(BaseModel):
    semesterId: uuid.UUID
    classId: uuid.UUID
    grades: List[GradeItem]

# =========================
# LOGGING HELPER
# =========================
def log_action(db: Session, user_id: str, action: str, detail: str):
    user = db.query(User).filter(User.id == user_id).first()
    new_log = ActivityLog(
        user_id=user.id if user else None,
        user_name=user.name if user else "System",
        action=action,
        detail=detail
    )
    db.add(new_log)
    db.commit()

# =========================
# 1. INTELLIGENCE (STATS & LOGS)
# =========================
@router.get("/stats/executive", summary="Global Executive Summary")
def get_executive_summary(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    total_students = db.query(Student).count()
    total_musyrif = db.query(User).filter(User.role == 1).count()
    reports_today = db.query(Report).filter(Report.report_date == date.today()).count()
    
    profiles = db.query(KMSProfile).all()
    if not profiles:
        avg_karakter = avg_mental = avg_softskill = 0
    else:
        avg_karakter = sum(p.karakter_score for p in profiles) / len(profiles)
        avg_mental = sum(p.mental_score for p in profiles) / len(profiles)
        avg_softskill = sum(p.softskill_score for p in profiles) / len(profiles)

    critical_count = db.query(KMSProfile).filter(KMSProfile.overall_score < 50).count()

    return {
        "data": {
            "stats": {
                "total_students": total_students,
                "total_musyrif": total_musyrif,
                "reports_today": reports_today,
                "critical_students": critical_count
            },
            "averages": {
                "karakter": round(avg_karakter, 1),
                "mental": round(avg_mental, 1),
                "softskill": round(avg_softskill, 1)
            }
        },
        "message": "Executive stats retrieved successfully"
    }

@router.get("/stats/distribution", summary="Performance Distribution for Radar Chart")
def get_performance_distribution(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    profiles = db.query(KMSProfile).all()
    if not profiles:
        values = [0, 0, 0]
    else:
        avg_karakter = sum(p.karakter_score for p in profiles) / len(profiles)
        avg_mental = sum(p.mental_score for p in profiles) / len(profiles)
        avg_softskill = sum(p.softskill_score for p in profiles) / len(profiles)
        values = [round(avg_karakter, 1), round(avg_mental, 1), round(avg_softskill, 1)]

    data = {
        "labels": ["Karakter", "Mental", "Softskill"],
        "values": values
    }
    return {
        "data": data,
        "message": "Performance distribution retrieved successfully"
    }

@router.get("/logs", summary="Recent Activity Logs")
def get_activity_logs(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10).all()
    result = []
    for log in logs:
        result.append({
            "time": log.created_at.isoformat(),
            "action": log.action,
            "user": log.user_name,
            "detail": log.detail
        })
    return {
        "data": result,
        "message": "Activity logs retrieved successfully"
    }

# =========================
# 2. MUSYRIF MANAGEMENT
# =========================
@router.get("/musyrif", summary="List All Musyrif")
def list_musyrif(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    musyrifs = db.query(User).filter(User.role == 1).all()
    result = []
    for m in musyrifs:
        count = db.query(Student).filter(Student.musyrif_id == m.id).count()
        # Calculate performance based on reports count vs average (simplified)
        report_count = db.query(Report).filter(Report.musyrif_id == m.id).count()
        performance = min(100.0, (report_count / 10) * 100) if report_count > 0 else 0
        
        m_dict = {
            "id": str(m.id),
            "name": m.name,
            "email": m.email,
            "nip": m.nip,
            "unit": m.unit,
            "students_count": count,
            "performance": round(performance, 1)
        }
        result.append(m_dict)
    return {
        "data": result,
        "message": "Musyrif list retrieved successfully"
    }

@router.post("/musyrif", summary="Create New Musyrif")
def create_musyrif(data: MusyrifCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    
    new_user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=1,
        phone=data.phone,
        nip=data.nip,
        unit=data.unit
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email sudah terdaftar (Integrity Error)")
    db.refresh(new_user)
    log_action(db, admin.get("sub"), "CREATE_MUSYRIF", f"Created account for {new_user.name}")
    return {
        "data": UserResponse.from_orm(new_user),
        "message": "Musyrif created successfully"
    }

@router.get("/musyrif/{id}", summary="Detailed Musyrif Personnel File")
def get_musyrif_detail(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    musyrif = db.query(User).filter(User.id == id, User.role == 1).first()
    if not musyrif:
        raise HTTPException(status_code=404, detail="Musyrif tidak ditemukan")
    
    # Get stats
    report_count = db.query(Report).filter(Report.musyrif_id == musyrif.id).count()
    effectiveness = min(100.0, (report_count / 10) * 100) if report_count > 0 else 0

    # Get assigned students (domain)
    students = db.query(Student).filter(Student.musyrif_id == id).all()
    student_list = []
    for s in students:
        student_list.append({
            "id": str(s.id),
            "name": s.name,
            "kelas": s.kelas,
            "status": "Aktif" if s.is_active else "Tidak Aktif"
        })
    
    return {
        "data": {
            "profile": musyrif,
            "stats": {
                "total_reports": report_count,
                "effectiveness": round(effectiveness, 1)
            },
            "domain": student_list
        },
        "message": "Musyrif detail retrieved"
    }

@router.put("/musyrif/{id}/domain", summary="Bulk Update Musyrif Domain")
def update_musyrif_domain(id: str, student_ids: list[uuid.UUID], db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    # Verify musyrif exists
    musyrif = db.query(User).filter(User.id == id, User.role == 1).first()
    if not musyrif:
        raise HTTPException(status_code=404, detail="Musyrif tidak ditemukan")
    
    # First, unassign all students currently assigned to this musyrif
    db.query(Student).filter(Student.musyrif_id == id).update({Student.musyrif_id: None})
    
    # Then assign the new ones
    if student_ids:
        db.query(Student).filter(Student.id.in_(student_ids)).update({Student.musyrif_id: id})
    
    db.commit()
    return {
        "data": None,
        "message": f"Domain {musyrif.name} updated successfully"
    }

@router.delete("/musyrif/{id}", summary="Delete Musyrif Account")
def delete_musyrif(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    musyrif = db.query(User).filter(User.id == id, User.role == 1).first()
    if not musyrif:
        raise HTTPException(status_code=404, detail="Musyrif tidak ditemukan")
    
    name = musyrif.name
    
    # Lepaskan relasi agar tidak error constraint (FK)
    # 1. Update students yang dibimbing musyrif ini
    db.query(Student).filter(Student.musyrif_id == id).update({Student.musyrif_id: None})
    
    # 2. Update reports yang dibuat musyrif ini
    db.query(Report).filter(Report.musyrif_id == id).update({Report.musyrif_id: None})
    
    # 3. Update activity logs yang dilakukan musyrif ini
    db.query(ActivityLog).filter(ActivityLog.user_id == id).update({ActivityLog.user_id: None})
    
    # 4. Update analysis snapshots yang dilakukan musyrif ini
    db.query(StudentAnalysisSnapshot).filter(StudentAnalysisSnapshot.performed_by == id).update({StudentAnalysisSnapshot.performed_by: None})

    db.delete(musyrif)
    db.commit()
    
    log_action(db, admin.get("sub"), "DELETE_MUSYRIF", f"Deleted account for {name}")
    return {
        "data": None,
        "message": "Musyrif deleted successfully"
    }

# =========================
# 3. STUDENT MANAGEMENT
# =========================
@router.get("/students")
def get_all_students(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    students = db.query(Student).all()
    # Flatten musyrif name for easier UI handling
    result = []
    for s in students:
        s_dict = {
            "id": str(s.id),
            "nis": s.nis,
            "name": s.name,
            "kelas": s.kelas,
            "angkatan": s.angkatan,
            "status": "Aktif" if s.is_active else "Tidak Aktif",
            "musyrif": s.musyrif.name if s.musyrif else "Unassigned",
            "musyrif_id": str(s.musyrif_id) if s.musyrif_id else None
        }
        result.append(s_dict)
    return {
        "data": result,
        "message": "Student list retrieved successfully"
    }

@router.get("/students/{id}", summary="Get Single Student Detail for Admin")
def get_admin_student_detail(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")
    
    # Get latest analysis snapshot for treatment recommendation
    snapshot = db.query(StudentAnalysisSnapshot).filter(
        StudentAnalysisSnapshot.student_id == id
    ).order_by(StudentAnalysisSnapshot.performed_at.desc()).first()
    
    treatment_summary = "Belum ada analisis mendalam."
    if snapshot:
        try:
            tk = json.loads(snapshot.treatment_k or "[]")
            tm = json.loads(snapshot.treatment_m or "[]")
            ts = json.loads(snapshot.treatment_s or "[]")
            all_treatments = tk + tm + ts
            if all_treatments:
                treatment_summary = "; ".join([t.get("main_name", "") for t in all_treatments[:3] if t.get("main_name")])
        except Exception:
            treatment_summary = snapshot.insight or "Belum ada analisis mendalam."

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
            "musyrif": student.musyrif.name if student.musyrif else "Unassigned",
            "musyrif_id": str(student.musyrif_id) if student.musyrif_id else None,
            "is_active": student.is_active,
            "treatment": treatment_summary
        },
        "message": "Student detail retrieved successfully"
    }

@router.post("/students")
def create_student(data: StudentCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = Student(**data.dict())
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="NIS sudah terdaftar atau format salah")
    db.refresh(student)
    log_action(db, admin.get("sub"), "CREATE_STUDENT", f"Enrolled student {student.name} (NIS: {student.nis})")
    return {
        "data": StudentResponse.from_orm(student),
        "message": "Student created successfully"
    }

@router.patch("/students/{id}/assign-musyrif", summary="Set Musyrif Domain for Student")
def assign_musyrif(id: str, musyrif_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")
    
    # Verify musyrif exists
    musyrif = db.query(User).filter(User.id == musyrif_id, User.role == 1).first()
    if not musyrif:
        raise HTTPException(status_code=404, detail="Musyrif tidak ditemukan")
    
    student.musyrif_id = musyrif_id
    db.commit()
    db.refresh(student)
    return {
        "data": {
            "student_name": student.name,
            "musyrif_name": musyrif.name
        },
        "message": "Musyrif assigned successfully"
    }

@router.get("/students/{id}/latest-analysis")
def get_latest_student_analysis(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    latest_report = db.query(Report).filter(Report.student_id == id).order_by(Report.report_date.desc()).first()
    if not latest_report:
        return {"data": None, "message": "No reports found for this student"}
    
    analysis = db.query(ReportAnalysis).filter(ReportAnalysis.report_id == latest_report.id).first()
    return {
        "data": {
            "insight": analysis.insight if analysis else "No analysis available yet.",
            "date": latest_report.report_date
        },
        "message": "Latest analysis retrieved"
    }

@router.put("/students/{id}")
def update_student(id: str, data: StudentUpdate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")
    
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(student, key, value)
    
    db.commit()
    db.refresh(student)
    log_action(db, admin.get("sub"), "UPDATE_STUDENT", f"Updated profile for {student.name}")
    return {
        "data": jsonable_encoder(student),
        "message": "Student updated successfully"
    }

@router.delete("/students/{id}")
def delete_student(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")
    name = student.name
    db.delete(student)
    db.commit()
    log_action(db, admin.get("sub"), "DELETE_STUDENT", f"Removed student record for {name}")
    return {
        "data": None,
        "message": "Student deleted successfully"
    }

@router.get("/students/export")
def export_students(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    students = db.query(Student).all()
    # In a real app, this would generate a CSV file. For now, we return the data.
    return {
        "data": students,
        "message": "Student records retrieved for export"
    }

# =========================
# 4. KMS CONFIGURATION
# =========================
@router.get("/kms/pillars")
def list_pillars(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    pillars = ["karakter", "mental", "softskill"]
    data = []
    for p in pillars:
        count = db.query(KMSMainIndicator).filter(KMSMainIndicator.category == p).count()
        data.append({
            "id": p,
            "name": p.capitalize(),
            "indicators_count": count
        })
    return {
        "data": data,
        "message": "Pillars retrieved successfully"
    }

# =========================
# KMS MAIN INDICATORS
# =========================
@router.get("/kms/indicators")
def list_indicators(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    indicators = db.query(KMSMainIndicator).all()
    return {
        "data": [KMSIndicatorResponse.from_orm(i) for i in indicators],
        "message": "Indicators retrieved successfully"
    }

@router.post("/kms/indicators")
def create_indicator(data: KMSIndicatorCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    indicator = KMSMainIndicator(**data.dict())
    db.add(indicator)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Indikator sudah ada atau format salah")
    db.refresh(indicator)
    log_action(db, admin.get("sub"), "CREATE_KMS_INDICATOR", f"Added KMS Indicator: {indicator.name} ({indicator.category})")
    return {
        "data": KMSIndicatorResponse.from_orm(indicator),
        "message": "Indicator created successfully"
    }

@router.put("/kms/indicators/{id}")
def update_indicator(id: str, data: KMSIndicatorCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    indicator = db.query(KMSMainIndicator).filter(KMSMainIndicator.id == id).first()
    if not indicator:
        raise HTTPException(status_code=404, detail="Indikator tidak ditemukan")
    
    for key, value in data.dict().items():
        setattr(indicator, key, value)
    
    db.commit()
    db.refresh(indicator)
    log_action(db, admin.get("sub"), "UPDATE_KMS_INDICATOR", f"Updated KMS Indicator: {indicator.name}")
    return {
        "data": KMSIndicatorResponse.from_orm(indicator),
        "message": "Indicator updated successfully"
    }

@router.delete("/kms/indicators/{id}")
def delete_indicator(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    indicator = db.query(KMSMainIndicator).filter(KMSMainIndicator.id == id).first()
    if not indicator:
        raise HTTPException(status_code=404, detail="Indikator tidak ditemukan")
    
    db.query(StudentAchievement).filter(StudentAchievement.parameter_id == indicator.id).delete()
    
    name = indicator.name
    cat = indicator.category
    db.delete(indicator)  # cascade ke details
    db.commit()
    log_action(db, admin.get("sub"), "DELETE_KMS_INDICATOR", f"Deleted indicator {name} from {cat}")
    return {
        "data": None,
        "message": "Indicator deleted successfully"
    }

# =========================
# KMS DETAIL INDICATORS
# =========================
@router.get("/kms/indicators/{id}/details", summary="List Detail Indicators for a Main Indicator")
def list_detail_indicators(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    indicator = db.query(KMSMainIndicator).filter(KMSMainIndicator.id == id).first()
    if not indicator:
        raise HTTPException(status_code=404, detail="Indikator utama tidak ditemukan")
    return {
        "data": [{"id": str(d.id), "indicator_detail": d.indicator_detail} for d in indicator.details],
        "message": "Detail indicators retrieved successfully"
    }

@router.post("/kms/indicators/{id}/details", summary="Add a Detail Indicator")
def add_detail_indicator(id: str, data: KMSDetailCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    indicator = db.query(KMSMainIndicator).filter(KMSMainIndicator.id == id).first()
    if not indicator:
        raise HTTPException(status_code=404, detail="Indikator utama tidak ditemukan")
    
    detail = KMSDetailIndicator(
        main_indicator_id=indicator.id,
        indicator_detail=data.indicator_detail
    )
    db.add(detail)
    db.commit()
    db.refresh(detail)
    log_action(db, admin.get("sub"), "CREATE_KMS_DETAIL", f"Added detail to {indicator.name}: {detail.indicator_detail[:40]}")
    return {
        "data": {"id": str(detail.id), "indicator_detail": detail.indicator_detail},
        "message": "Detail indicator added successfully"
    }

@router.put("/kms/indicators/{id}/details/{detail_id}", summary="Update a Detail Indicator")
def update_detail_indicator(id: str, detail_id: str, data: KMSDetailCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    detail = db.query(KMSDetailIndicator).filter(
        KMSDetailIndicator.id == detail_id,
        KMSDetailIndicator.main_indicator_id == id
    ).first()
    if not detail:
        raise HTTPException(status_code=404, detail="Indikator detail tidak ditemukan")
    
    detail.indicator_detail = data.indicator_detail
    db.commit()
    db.refresh(detail)
    return {
        "data": {"id": str(detail.id), "indicator_detail": detail.indicator_detail},
        "message": "Detail indicator updated successfully"
    }

@router.delete("/kms/indicators/{id}/details/{detail_id}", summary="Delete a Detail Indicator")
def delete_detail_indicator(id: str, detail_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    detail = db.query(KMSDetailIndicator).filter(
        KMSDetailIndicator.id == detail_id,
        KMSDetailIndicator.main_indicator_id == id
    ).first()
    if not detail:
        raise HTTPException(status_code=404, detail="Indikator detail tidak ditemukan")
    
    db.delete(detail)
    db.commit()
    log_action(db, admin.get("sub"), "DELETE_KMS_DETAIL", f"Deleted detail indicator: {detail.indicator_detail[:40]}")
    return {
        "data": None,
        "message": "Detail indicator deleted successfully"
    }

# =========================
# 5. ACADEMIC PERIODS (SEMESTERS)
# =========================
@router.get("/academic/semesters")
def list_semesters(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sems = db.query(Semester).all()
    return {
        "data": jsonable_encoder(sems),
        "message": "Semesters retrieved successfully"
    }

@router.get("/academic/semesters/{id}")
def get_semester_detail(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester tidak ditemukan")
    
    # Get students performance summary (mocked or aggregated if possible)
    # For now, let's just return the students list
    students = db.query(Student).all()
    student_list = []
    for s in students:
        student_list.append({
            "id": str(s.id),
            "name": s.name,
            "k": 75, # Mocked for now, needs real aggregation logic later
            "m": 80,
            "s": 70
        })

    return {
        "data": {
            "semester": jsonable_encoder(sem),
            "stats": {
                "total_students": len(student_list),
                "active_faculty": db.query(User).filter(User.role == 1).count()
            },
            "students": student_list
        },
        "message": "Semester detail retrieved"
    }

@router.post("/academic/semesters")
def create_semester(data: SemesterCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    if data.is_active:
        db.query(Semester).update({Semester.is_active: False})
    
    sem = Semester(**data.dict())
    db.add(sem)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Data semester konflik atau format salah")
    db.refresh(sem)
    log_action(db, admin.get("sub"), "CREATE_SEMESTER", f"Created academic period: {sem.name}")
    return {
        "data": SemesterResponse.from_orm(sem),
        "message": "Semester created successfully"
    }

@router.put("/academic/semesters/{id}", summary="Update Full Semester Data")
def update_semester(id: str, data: SemesterCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester tidak ditemukan")
    
    # If this semester is being set to active, deactivate all others
    if data.is_active and not sem.is_active:
        db.query(Semester).filter(Semester.id != id).update({Semester.is_active: False})
    
    for key, value in data.dict().items():
        setattr(sem, key, value)
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Update semester konflik")
    
    db.refresh(sem)
    return {
        "data": jsonable_encoder(sem),
        "message": "Semester updated successfully"
    }

@router.patch("/academic/semesters/{id}", summary="Quick Toggle Semester Status")
def patch_semester(id: str, is_active: bool, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester tidak ditemukan")
    
    if is_active:
        db.query(Semester).update({Semester.is_active: False})
    
    sem.is_active = is_active
    db.commit()
    db.refresh(sem)
    return {
        "data": jsonable_encoder(sem),
        "message": "Semester status updated"
    }

@router.get("/academic/semesters/{id}/performance/export", summary="Export Performance Data for 1 Semester")
def export_semester_performance(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    semester = db.query(Semester).filter(Semester.id == id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester tidak ditemukan")
    
    profiles = db.query(KMSProfile, Student).join(Student, KMSProfile.student_id == Student.id).filter(KMSProfile.semester_id == id).all()
    
    export_data = []
    for profile, student in profiles:
        export_data.append({
            "nis": student.nis,
            "name": student.name,
            "kelas": student.kelas,
            "karakter": profile.karakter_score,
            "mental": profile.mental_score,
            "softskill": profile.softskill_score,
            "overall": profile.overall_score,
            "report_count": profile.report_count
        })
    
    return {
        "data": {
            "semester_name": semester.name,
            "records": export_data
        },
        "message": "Performance data exported successfully"
    }

@router.post("/academic/semesters/{id}/analyze-all", summary="Batch Analysis for All Students in Semester")
def analyze_all_students(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    semester = db.query(Semester).filter(Semester.id == id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester tidak ditemukan")
    
    # 1. Get all students
    students = db.query(Student).filter(Student.is_active == True).all()
    
    processed_count = 0
    for student in students:
        # 2. Get all analyzed reports for this student in this semester
        reports = db.query(Report).filter(
            Report.student_id == student.id,
            Report.semester_id == id,
            Report.status == "analyzed"
        ).all()
        
        if not reports:
            continue
            
        # 3. Aggregate Detections
        # This logic mimics the profiling service
        report_ids = [r.id for r in reports]
        analyses = db.query(ReportAnalysis).filter(ReportAnalysis.report_id.in_(report_ids)).all()
        analysis_ids = [a.id for a in analyses]
        
        detections = db.query(ReportParameterDetection).filter(
            ReportParameterDetection.report_analysis_id.in_(analysis_ids)
        ).all()
        
        # Simple count logic for scores (simulation)
        gained_karakter = len([d for d in detections if d.status_detected == "gained" and db.query(KMSMainIndicator).filter(KMSMainIndicator.id == d.parameter_id, KMSMainIndicator.category == "karakter").first()])
        gained_mental = len([d for d in detections if d.status_detected == "gained" and db.query(KMSMainIndicator).filter(KMSMainIndicator.id == d.parameter_id, KMSMainIndicator.category == "mental").first()])
        gained_softskill = len([d for d in detections if d.status_detected == "gained" and db.query(KMSMainIndicator).filter(KMSMainIndicator.id == d.parameter_id, KMSMainIndicator.category == "softskill").first()])
        
        # Update Profile
        profile = db.query(KMSProfile).filter(KMSProfile.student_id == student.id, KMSProfile.semester_id == id).first()
        if not profile:
            profile = KMSProfile(student_id=student.id, semester_id=id)
            db.add(profile)
            
        profile.karakter_score = min(100.0, (gained_karakter / 40) * 100)
        profile.mental_score = min(100.0, (gained_mental / 34) * 100)
        profile.softskill_score = min(100.0, (gained_softskill / 14) * 100)
        profile.overall_score = (profile.karakter_score + profile.mental_score + profile.softskill_score) / 3
        profile.report_count = len(reports)
        profile.last_updated = datetime.utcnow()
        
        processed_count += 1
        
    db.commit()
    
    return {
        "data": {"processed_students": processed_count},
        "message": f"Global analysis completed for {processed_count} students"
    }

@router.delete("/academic/semesters/{id}")
def delete_semester(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester tidak ditemukan")
    name = sem.name
    db.delete(sem)
    db.commit()
    log_action(db, admin.get("sub"), "DELETE_SEMESTER", f"Removed academic period {name}")
    return {
        "data": None,
        "message": "Semester deleted successfully"
    }


# =========================
# 5B. ACADEMIC CLASSES & GRADES
# =========================

@router.get("/academic/semesters/{semester_id}/classes")
def get_classes(
    semester_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    classes = db.query(AcademicClass).filter(
        AcademicClass.semester_id == semester_id
    ).all()
    return {
        "data": jsonable_encoder(classes),
        "message": "Classes retrieved successfully"
    }

@router.post("/academic/semesters/{semester_id}/classes")
def create_class(
    semester_id: uuid.UUID,
    data: AcademicClassCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    new_class = AcademicClass(
        name=data.name,
        semester_id=semester_id
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    log_action(db, admin.get("sub"), "CREATE_CLASS", f"Created academic class: {new_class.name}")
    return {
        "data": jsonable_encoder(new_class),
        "message": "Class created successfully"
    }

@router.put("/academic/classes/{class_id}")
def update_class(
    class_id: uuid.UUID,
    data: AcademicClassCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    cls = db.query(AcademicClass).filter(AcademicClass.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    
    cls.name = data.name
    db.commit()
    db.refresh(cls)
    log_action(db, admin.get("sub"), "UPDATE_CLASS", f"Updated academic class: {cls.name}")
    return {
        "data": jsonable_encoder(cls),
        "message": "Class updated successfully"
    }

@router.delete("/academic/classes/{class_id}")
def delete_class(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    cls = db.query(AcademicClass).filter(AcademicClass.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    
    name = cls.name
    db.delete(cls)
    db.commit()
    log_action(db, admin.get("sub"), "DELETE_CLASS", f"Deleted academic class: {name}")
    return {
        "data": None,
        "message": "Class deleted successfully"
    }

@router.get("/academic/classes/{class_id}/students")
def get_students(
    class_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    students = (
        db.query(Student)
        .join(ClassStudent, ClassStudent.student_id == Student.id)
        .filter(ClassStudent.class_id == class_id)
        .all()
    )
    return {
        "data": jsonable_encoder(students),
        "message": "Students retrieved successfully"
    }

@router.post("/academic/classes/{class_id}/students")
def assign_students(
    class_id: uuid.UUID,
    student_ids: list[uuid.UUID],
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    cls = db.query(AcademicClass).filter(AcademicClass.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    
    # Hapus relasi yang lama
    db.query(ClassStudent).filter(ClassStudent.class_id == class_id).delete()
    
    # Tambahkan relasi baru
    for sid in student_ids:
        db.add(ClassStudent(class_id=class_id, student_id=sid))
        
    db.commit()
    return {
        "data": None,
        "message": "Students assigned to class successfully"
    }

@router.get("/academic/classes/{class_id}/grades")
def get_class_grades(
    class_id: uuid.UUID,
    semester_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    grades = db.query(StudentGrade).filter(
        StudentGrade.class_id == class_id,
        StudentGrade.semester_id == semester_id
    ).all()
    return {
        "data": jsonable_encoder(grades),
        "message": "Grades retrieved successfully"
    }


@router.post("/academic/grades/upsert")
def upsert_grades(
    payload: GradePayload,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    for g in payload.grades:
        stmt = insert(StudentGrade).values(
            student_id=g.studentId,
            class_id=payload.classId,
            semester_id=payload.semesterId,
            nh=g.nh,
            nb=g.nb,
            na=g.na
        ).on_conflict_do_update(
            index_elements=["student_id", "class_id", "semester_id"],
            set_={
                "nh": g.nh,
                "nb": g.nb,
                "na": g.na
            }
        )

        db.execute(stmt)

    db.commit()

    return {"message": "Grades upserted successfully"}


# =========================
# 6. ANALISIS KUMULATIF (ADMIN)
# =========================
from app.services.analysis_service import run_analysis_for_student, format_full_snapshot
from app.models.models import StudentAnalysisSnapshot
from typing import Optional

@router.post("/analyze/student/{student_id}", summary="Admin: Analisis 1 Student")
def admin_analyze_student(
    student_id: str,
    semester_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")

    result = run_analysis_for_student(student_id, semester_id, admin.get("sub"), db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    log_action(db, admin.get("sub"), "ANALYZE_STUDENT",
               f"Ran cumulative analysis for {student.name} (semester {semester_id[:8]})")
    return {
        "data": result,
        "message": f"Analisis kumulatif untuk {student.name} berhasil."
    }


@router.post("/analyze/domain/{musyrif_id}", summary="Admin: Analisis Semua Student 1 Domain Musyrif")
def admin_analyze_domain(
    musyrif_id: str,
    semester_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    musyrif = db.query(User).filter(User.id == musyrif_id, User.role == 1).first()
    if not musyrif:
        raise HTTPException(status_code=404, detail="Musyrif tidak ditemukan")

    students = db.query(Student).filter(
        Student.musyrif_id == musyrif_id,
        Student.is_active == True
    ).all()

    results, errors = [], []
    for student in students:
        try:
            res = run_analysis_for_student(str(student.id), semester_id, admin.get("sub"), db)
            if "error" in res:
                errors.append({"student_id": str(student.id), "name": student.name, "error": res["error"]})
            else:
                results.append({"student_id": str(student.id), "name": student.name, "snapshot_id": res["snapshot_id"]})
        except Exception as e:
            errors.append({"student_id": str(student.id), "name": student.name, "error": str(e)})

    log_action(db, admin.get("sub"), "ANALYZE_DOMAIN",
               f"Batch analysis for domain {musyrif.name}: {len(results)} OK, {len(errors)} failed")
    return {
        "data": {"processed": len(results), "skipped": len(errors), "results": results, "errors": errors},
        "message": f"Analisis domain {musyrif.name} selesai."
    }


@router.post("/analyze/all", summary="Admin: Analisis Semua Student Aktif")
def admin_analyze_all(
    semester_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    students = db.query(Student).filter(Student.is_active == True).all()
    results, errors = [], []
    for student in students:
        try:
            res = run_analysis_for_student(str(student.id), semester_id, admin.get("sub"), db)
            if "error" in res:
                errors.append({"student_id": str(student.id), "name": student.name, "error": res["error"]})
            else:
                results.append({"student_id": str(student.id), "name": student.name, "snapshot_id": res["snapshot_id"]})
        except Exception as e:
            errors.append({"student_id": str(student.id), "name": student.name, "error": str(e)})

    log_action(db, admin.get("sub"), "ANALYZE_ALL",
               f"Global batch analysis: {len(results)} OK, {len(errors)} failed")
    return {
        "data": {"processed": len(results), "skipped": len(errors), "results": results, "errors": errors},
        "message": f"Analisis global selesai: {len(results)} berhasil, {len(errors)} dilewati."
    }


# =========================
# 7. HISTORY LAPORAN (ADMIN)
# =========================
@router.get("/history/reports/{student_id}", summary="Admin: History Laporan Student")
def admin_get_report_history(
    student_id: str,
    semester_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    from datetime import date as date_type
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")

    from sqlalchemy import desc as _desc
    query = db.query(Report).filter(Report.student_id == student_id)
    if semester_id:
        query = query.filter(Report.semester_id == semester_id)
    if from_date:
        query = query.filter(Report.report_date >= date_type.fromisoformat(from_date))
    if to_date:
        query = query.filter(Report.report_date <= date_type.fromisoformat(to_date))

    total = query.count()
    reports = query.order_by(_desc(Report.report_date)).offset((page - 1) * size).limit(size).all()

    items = [{
        "id": str(r.id),
        "date": r.report_date.isoformat() if r.report_date else None,
        "status": r.status,
        "transcript": r.transcript,
        "semester_id": str(r.semester_id) if r.semester_id else None,
        "musyrif_id": str(r.musyrif_id) if r.musyrif_id else None,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in reports]

    return {
        "data": {
            "student_name": student.name,
            "items": items,
            "pagination": {"page": page, "size": size, "total": total, "total_pages": (total + size - 1) // size}
        },
        "message": f"History laporan {student.name} berhasil diambil."
    }


# =========================
# 8. HISTORY ANALISIS (ADMIN)
# =========================
@router.get("/history/analysis/{student_id}", summary="Admin: Daftar Snapshot Analisis Student")
def admin_get_analysis_history(
    student_id: str,
    semester_id: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student tidak ditemukan")

    query = db.query(StudentAnalysisSnapshot).filter(StudentAnalysisSnapshot.student_id == student_id)
    if semester_id:
        query = query.filter(StudentAnalysisSnapshot.semester_id == semester_id)

    total = query.count()
    snapshots = query.order_by(StudentAnalysisSnapshot.performed_at.desc()).offset((page - 1) * size).limit(size).all()

    items = [{
        "snapshot_id": str(s.id),
        "performed_at": s.performed_at.isoformat(),
        "performed_by": str(s.performed_by) if s.performed_by else None,
        "semester_id": str(s.semester_id),
        "reports_included": s.reports_included,
        "scores": {
            "karakter": s.karakter_score,
            "mental": s.mental_score,
            "softskill": s.softskill_score,
            "overall": s.overall_score
        }
    } for s in snapshots]

    return {
        "data": {
            "student_name": student.name,
            "items": items,
            "pagination": {"page": page, "size": size, "total": total, "total_pages": (total + size - 1) // size}
        },
        "message": "Daftar snapshot analisis berhasil diambil."
    }


@router.get("/history/analysis/{student_id}/{snapshot_id}", summary="Admin: Detail Lengkap 1 Snapshot Analisis")
def admin_get_analysis_detail(
    student_id: str,
    snapshot_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    snapshot = db.query(StudentAnalysisSnapshot).filter(
        StudentAnalysisSnapshot.id == snapshot_id,
        StudentAnalysisSnapshot.student_id == student_id
    ).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot tidak ditemukan")

    return {
        "data": format_full_snapshot(snapshot, db),
        "message": "Detail snapshot berhasil diambil."
    }

