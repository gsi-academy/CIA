from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
import uuid

from typing import List

from app.database import SessionLocal
from app.models.models import (
    User, Student, Semester, KMSParameter, Report, KMSProfile
)
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

from app.schemas.auth import MusyrifCreate
from app.schemas.santri import SantriCreate
from app.schemas.semester import SemesterCreate
from app.schemas.kms import KMSParamCreate

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

    return {
        "data": {
            "stats": {
                "total_students": total_students,
                "total_musyrif": total_musyrif,
                "reports_today": reports_today
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
    # Mocking distribution data
    data = {
        "labels": ["Karakter", "Mental", "Softskill"],
        "values": [85, 70, 90]
    }
    return {
        "data": data,
        "message": "Performance distribution retrieved successfully"
    }

@router.get("/logs", summary="Recent Activity Logs")
def get_activity_logs(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    # Mocking logs for now
    logs = [
        {"time": datetime.utcnow().isoformat(), "action": "CREATE_STUDENT", "user": "Admin", "detail": "Added Ahmad"},
        {"time": datetime.utcnow().isoformat(), "action": "LOGIN", "user": "Musyrif 1", "detail": "Logged in from IP 1.2.3.4"},
    ]
    return {
        "data": logs,
        "message": "Activity logs retrieved successfully"
    }

# =========================
# 2. MUSYRIF MANAGEMENT
# =========================
@router.get("/musyrif", summary="List All Musyrif")
def list_musyrif(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    musyrifs = db.query(User).filter(User.role == 1).all()
    return {
        "data": musyrifs,
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
    db.commit()
    db.refresh(new_user)
    return {
        "data": new_user,
        "message": "Musyrif created successfully"
    }

@router.get("/musyrif/{id}", summary="Musyrif Performance Detail")
def get_musyrif_detail(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    musyrif = db.query(User).filter(User.id == id, User.role == 1).first()
    if not musyrif:
        raise HTTPException(status_code=404, detail="Musyrif tidak ditemukan")
    
    # Mocking effectiveness stats
    data = {
        "profile": musyrif,
        "stats": {
            "total_reports": db.query(Report).filter(Report.musyrif_id == musyrif.id).count(),
            "effectiveness": 92.5
        }
    }
    return {
        "data": data,
        "message": "Musyrif detail retrieved successfully"
    }

# =========================
# 3. STUDENT MANAGEMENT
# =========================
@router.get("/students")
def get_all_students(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    students = db.query(Student).all()
    return {
        "data": students,
        "message": "Student list retrieved successfully"
    }

@router.post("/students")
def create_student(data: SantriCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = Student(**data.dict())
    db.add(student)
    db.commit()
    db.refresh(student)
    return {
        "data": student,
        "message": "Student created successfully"
    }

@router.put("/students/{id}")
def update_student(id: str, data: SantriCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Santri tidak ditemukan")
    
    for key, value in data.dict().items():
        setattr(student, key, value)
    
    db.commit()
    db.refresh(student)
    return {
        "data": student,
        "message": "Student updated successfully"
    }

@router.delete("/students/{id}")
def delete_student(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Santri tidak ditemukan")
    db.delete(student)
    db.commit()
    return {
        "data": None,
        "message": "Student deleted successfully"
    }

@router.get("/students/export")
def export_students(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    # Mocking export
    return {
        "data": {"download_url": "/api/v1/admin/static/students_export.csv"},
        "message": "Export prepared successfully"
    }

# =========================
# 4. KMS CONFIGURATION
# =========================
@router.get("/kms/pillars")
def list_pillars(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    # Mocking pillars structure
    data = [
        {"id": "karakter", "name": "Karakter", "params_count": 40},
        {"id": "mental", "name": "Mental", "params_count": 34},
        {"id": "softskill", "name": "Softskill", "params_count": 14}
    ]
    return {
        "data": data,
        "message": "Pillars retrieved successfully"
    }

@router.get("/kms/parameters")
def list_parameters(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    params = db.query(KMSParameter).all()
    return {
        "data": params,
        "message": "Parameters retrieved successfully"
    }

@router.post("/kms/parameters")
def create_parameter(data: KMSParamCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    param = KMSParameter(**data.dict())
    db.add(param)
    db.commit()
    db.refresh(param)
    return {
        "data": param,
        "message": "Parameter created successfully"
    }

@router.put("/kms/parameters/{id}")
def update_parameter(id: str, data: KMSParamCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    param = db.query(KMSParameter).filter(KMSParameter.id == id).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter tidak ditemukan")
    
    for key, value in data.dict().items():
        setattr(param, key, value)
    
    db.commit()
    db.refresh(param)
    return {
        "data": param,
        "message": "Parameter updated successfully"
    }

@router.delete("/kms/parameters/{id}")
def delete_parameter(id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    param = db.query(KMSParameter).filter(KMSParameter.id == id).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter tidak ditemukan")
    db.delete(param)
    db.commit()
    return {
        "data": None,
        "message": "Parameter deleted successfully"
    }

# =========================
# 5. ACADEMIC PERIODS (SEMESTERS)
# =========================
@router.get("/academic/semesters")
def list_semesters(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sems = db.query(Semester).all()
    return {
        "data": sems,
        "message": "Semesters retrieved successfully"
    }

@router.post("/academic/semesters")
def create_semester(data: SemesterCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    if data.is_active:
        db.query(Semester).update({Semester.is_active: False})
    
    sem = Semester(**data.dict())
    db.add(sem)
    db.commit()
    db.refresh(sem)
    return {
        "data": sem,
        "message": "Semester created successfully"
    }

@router.patch("/academic/semesters/{id}")
def update_semester_status(id: str, is_active: bool, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    sem = db.query(Semester).filter(Semester.id == id).first()
    if not sem:
        raise HTTPException(status_code=404, detail="Semester tidak ditemukan")
    
    if is_active:
        db.query(Semester).update({Semester.is_active: False})
    
    sem.is_active = is_active
    db.commit()
    db.refresh(sem)
    return {
        "data": sem,
        "message": "Semester status updated successfully"
    }
