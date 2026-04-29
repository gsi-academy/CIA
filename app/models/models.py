# models.py

import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Date, TIMESTAMP, ForeignKey, Boolean, Float, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
from app.database import Base


# ================= ENUMS =================
class ReportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    analyzed = "analyzed"
    failed = "failed"

class TrendDirection(str, enum.Enum):
    improving = "improving"
    stable = "stable"
    declining = "declining"

class SentimentType(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"

class PriorityLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


# ================= USERS =================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(Integer)  # 0 admin, 1 musyrif
    
    # Tambahan profil
    phone = Column(String, nullable=True)
    nip = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    reports = relationship("Report", back_populates="musyrif")


# ================= SANTRI =================
class Student(Base): # Keep class name Student for compatibility
    __tablename__ = "santri"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nis = Column(String, unique=True)
    name = Column(String)
    kelas = Column(String)
    angkatan = Column(Integer)
    
    # Profile & Biodata
    birth_info = Column(String, nullable=True) # e.g. "Jakarta, 12 Mei 2005"
    address = Column(Text, nullable=True)
    guardian_name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    
    # Relationship with Musyrif
    musyrif_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    reports = relationship("Report", back_populates="santri")
    musyrif = relationship("User")


# ================= SEMESTERS =================
class Semester(Base):
    __tablename__ = "semesters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    academic_year = Column(String, nullable=True)
    semester_number = Column(Integer, nullable=True)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)





# ================= KMS PARAMETERS (MASTER) =================
class KMSMainIndicator(Base):
    __tablename__ = "kms_main_indicators"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String) # karakter, mental, softskill
    theme = Column(String)
    name = Column(String)
    description = Column(Text)
    weight = Column(Float, default=1.0)
    
    details = relationship("KMSDetailIndicator", back_populates="main_indicator", cascade="all, delete-orphan")

class KMSDetailIndicator(Base):
    __tablename__ = "kms_detail_indicators"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    main_indicator_id = Column(UUID(as_uuid=True), ForeignKey("kms_main_indicators.id", ondelete="CASCADE"))
    indicator_detail = Column(Text)
    action_template = Column(Text, nullable=True)  # Panduan tindakan musyrif, di-generate otomatis

    main_indicator = relationship("KMSMainIndicator", back_populates="details")

# ================= STUDENT ACHIEVEMENT (CURRENT STATE) =================
class StudentAchievement(Base):
    __tablename__ = "student_achievements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id", ondelete="CASCADE"))
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("kms_main_indicators.id", ondelete="CASCADE"))
    status = Column(String, default="undefined") # undefined, gained, negative
    evidence_excerpt = Column(Text, nullable=True)
    last_updated = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

# ================= REPORT =================
class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    musyrif_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id", ondelete="CASCADE"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))

    report_date = Column(Date)
    transcript = Column(Text)
    status = Column(String, default="pending")

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    musyrif = relationship("User", back_populates="reports")
    santri = relationship("Student", back_populates="reports")
    analysis = relationship("ReportAnalysis", back_populates="report", uselist=False)

# ================= ANALYSIS =================
class ReportAnalysis(Base):
    __tablename__ = "report_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"))

    insight = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    raw_llm_output = Column(Text, nullable=True)
    model_used = Column(String, nullable=True)
    processing_ms = Column(Integer, default=0)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    report = relationship("Report", back_populates="analysis")
    detections = relationship("ReportParameterDetection", back_populates="analysis")

# ================= PARAMETER DETECTION (HISTORY) =================
class ReportParameterDetection(Base):
    __tablename__ = "report_parameter_detections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_analysis_id = Column(UUID(as_uuid=True), ForeignKey("report_analyses.id", ondelete="CASCADE"))
    detail_parameter_id = Column(UUID(as_uuid=True), ForeignKey("kms_detail_indicators.id"))
    status_detected = Column(String) # gained, negative
    evidence = Column(Text)

    analysis = relationship("ReportAnalysis", back_populates="detections")

# ================= PROFILING / AGGREGATION =================
class KMSProfile(Base):
    __tablename__ = "kms_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id", ondelete="CASCADE"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))

    karakter_score = Column(Float, default=0.0) # (gained / 40) * 100
    mental_score = Column(Float, default=0.0)   # (gained / 34) * 100
    softskill_score = Column(Float, default=0.0) # (gained / 14) * 100
    overall_score = Column(Float, default=0.0)

    report_count = Column(Integer, default=0)
    last_updated = Column(TIMESTAMP, default=datetime.utcnow)

# ================= TREATMENTS =================
class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id", ondelete="CASCADE"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    generated_from_report = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"))

    recommendation = Column(Text)
    priority = Column(String, default="medium")
    status = Column(String, default="pending")
    musyrif_notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

# ================= ACTIVITY LOGS =================
class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_name = Column(String) # Redundant but faster for display
    action = Column(String) # e.g. CREATE_STUDENT, UPDATE_KMS, DELETE_MUSYRIF
    detail = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

# ================= CUMULATIVE ANALYSIS SNAPSHOTS =================
class StudentAnalysisSnapshot(Base):
    """
    Satu record per run analisis kumulatif. Data lama tidak dihapus, hanya ditambah.
    Menyimpan skor, insight, treatment, dan list indikator yang terdeteksi.
    """
    __tablename__ = "student_analysis_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id", ondelete="CASCADE"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    performed_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Cakupan laporan yang diproses dalam run ini
    reports_included = Column(Integer, default=0)
    analyzed_up_to = Column(TIMESTAMP, nullable=True)  # timestamp laporan terbaru yang diproses

    # Skor
    karakter_score = Column(Float, default=0.0)
    mental_score = Column(Float, default=0.0)
    softskill_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)

    # Hitungan detail (untuk transparansi)
    karakter_achieved = Column(Integer, default=0)
    karakter_total = Column(Integer, default=0)
    mental_achieved = Column(Integer, default=0)
    mental_total = Column(Integer, default=0)
    softskill_achieved = Column(Integer, default=0)
    softskill_total = Column(Integer, default=0)

    # Hasil narasi
    insight = Column(Text, nullable=True)

    # Treatment: JSON string → list of {detail_id, detail_text, main_name, main_id}
    treatment_k = Column(Text, nullable=True)
    treatment_m = Column(Text, nullable=True)
    treatment_s = Column(Text, nullable=True)

    # Relations
    detected_indicators = relationship(
        "SnapshotDetection",
        back_populates="snapshot",
        cascade="all, delete-orphan"
    )
    santri = relationship("Student")
    performer = relationship("User", foreign_keys=[performed_by])


class SnapshotDetection(Base):
    """
    Indikator detail yang berhasil terdeteksi dalam satu run analisis.
    Hanya menyimpan deteksi BARU pada run ini (bukan kumulatif ulang).
    """
    __tablename__ = "snapshot_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("student_analysis_snapshots.id", ondelete="CASCADE"))
    main_indicator_id = Column(UUID(as_uuid=True), ForeignKey("kms_main_indicators.id"))
    detail_indicator_id = Column(UUID(as_uuid=True), ForeignKey("kms_detail_indicators.id"))
    evidence_excerpt = Column(Text, nullable=True)

    snapshot = relationship("StudentAnalysisSnapshot", back_populates="detected_indicators")
    main_indicator = relationship("KMSMainIndicator")
    detail_indicator = relationship("KMSDetailIndicator")

# ================= ACADEMIC CLASS =================
class AcademicClass(Base):
    __tablename__ = "academic_classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)  # contoh: "QCB Kelas 2"
    
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id", ondelete="CASCADE"))
    
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    semester = relationship("Semester")
    students = relationship("ClassStudent", back_populates="kelas", cascade="all, delete")

    # ================= CLASS STUDENT =================
class ClassStudent(Base):
    __tablename__ = "class_students"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic_classes.id", ondelete="CASCADE"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("santri.id", ondelete="CASCADE"))

    kelas = relationship("AcademicClass", back_populates="students")
    student = relationship("Student")

    # ================= STUDENT GRADES =================
class StudentGrade(Base):
    __tablename__ = "student_grades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    student_id = Column(UUID(as_uuid=True), ForeignKey("santri.id", ondelete="CASCADE"))
    class_id = Column(UUID(as_uuid=True), ForeignKey("academic_classes.id", ondelete="CASCADE"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id", ondelete="CASCADE"))

    nh = Column(Float, default=0.0)
    nb = Column(Float, default=0.0)
    na = Column(Float, default=0.0)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔥 WAJIB (biar bisa UPSERT)
    __table_args__ = (
        UniqueConstraint("student_id", "class_id", "semester_id", name="uq_student_grade"),
    )

    student = relationship("Student")
    kelas = relationship("AcademicClass")
    semester = relationship("Semester")