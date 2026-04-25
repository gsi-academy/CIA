# models.py

import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Date, TIMESTAMP, ForeignKey, Boolean, Float, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
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
class Student(Base): # Keep class name Student for compatibility with my previous route fixes, but change table to santri
    __tablename__ = "santri"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nis = Column(String, unique=True)
    name = Column(String)
    kelas = Column(String)
    angkatan = Column(Integer)
    
    # Tambahan profil
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    reports = relationship("Report", back_populates="santri")


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
class KMSParameter(Base):
    __tablename__ = "kms_parameters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String) # karakter, mental, softskill
    theme = Column(String)
    name = Column(String)
    description = Column(Text)

# ================= STUDENT ACHIEVEMENT (CURRENT STATE) =================
class StudentAchievement(Base):
    __tablename__ = "student_achievements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("kms_parameters.id"))
    status = Column(String, default="undefined") # undefined, gained, negative
    evidence_excerpt = Column(Text, nullable=True)
    last_updated = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

# ================= REPORT =================
class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    musyrif_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
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
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))

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
    report_analysis_id = Column(UUID(as_uuid=True), ForeignKey("report_analyses.id"))
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("kms_parameters.id"))
    status_detected = Column(String) # gained, negative
    evidence = Column(Text)

    analysis = relationship("ReportAnalysis", back_populates="detections")

# ================= PROFILING / AGGREGATION =================
class KMSProfile(Base):
    __tablename__ = "kms_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
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
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    generated_from_report = Column(UUID(as_uuid=True), ForeignKey("reports.id"))

    recommendation = Column(Text)
    priority = Column(String, default="medium")
    status = Column(String, default="pending")
    musyrif_notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

