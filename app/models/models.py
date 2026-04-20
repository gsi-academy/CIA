import uuid
from datetime import datetime
import enum

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Float, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship

from app.database import Base


# =========================
# ENUM
# =========================
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

class KMSCode(str, enum.Enum):
    K = "K"
    M = "M"
    S = "S"


# =========================
# USERS
# =========================
class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint('role IN (0,1)', name='check_user_role_binary'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(Integer, default=1)  # 0: Admin, 1: Musyrif
    is_active = Column(Boolean, default=True)
    # Data tambahan musyrif
    phone = Column(String, nullable=True)
    nip = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # WAJIB ADA (biar tidak error relationship)
    reports = relationship("Report", back_populates="musyrif")

# =========================
# SANTRI
# =========================
class Santri(Base):
    __tablename__ = "santri"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nis = Column(String, unique=True)
    name = Column(String)
    date_of_birth = Column(Date)
    gender = Column(String)
    angkatan = Column(Integer)
    kelas = Column(String)
    photo_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # RELATIONSHIP (FIX)
    reports = relationship("Report", back_populates="santri")


# =========================
# SEMESTER
# =========================
class Semester(Base):
    __tablename__ = "semesters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    academic_year = Column(String)
    semester_number = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)


# =========================
# REPORTS (CORE)
# =========================
class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    musyrif_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))

    report_date = Column(Date)
    audio_url = Column(String)
    transcript = Column(Text)

    status = Column(ENUM(ReportStatus, name="report_status"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # RELATIONSHIP (FIX WAJIB)
    musyrif = relationship("User", back_populates="reports")
    santri = relationship("Santri", back_populates="reports")

    analysis = relationship("ReportAnalysis", back_populates="report", uselist=False)


# =========================
# REPORT ANALYSIS
# =========================
class ReportAnalysis(Base):
    __tablename__ = "report_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), unique=True)

    raw_llm_output = Column(JSONB)
    rag_context_used = Column(JSONB)
    model_used = Column(String)
    processing_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="analysis")
    variable_scores = relationship("ReportVariableScore", back_populates="analysis")


# =========================
# VARIABLE SCORES
# =========================
class ReportVariableScore(Base):
    __tablename__ = "report_variable_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_analysis_id = Column(UUID(as_uuid=True), ForeignKey("report_analyses.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
    kms_variable_id = Column(UUID(as_uuid=True), ForeignKey("kms_variables.id"))

    score = Column(Float)
    evidence_excerpt = Column(Text)
    sentiment = Column(ENUM(SentimentType, name="sentiment_type"))

    analysis = relationship("ReportAnalysis", back_populates="variable_scores")


# =========================
# KMS DIMENSIONS
# =========================
class KMSDimension(Base):
    __tablename__ = "kms_dimensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(ENUM(KMSCode, name="kms_code"))
    name = Column(String)
    description = Column(Text)
    weight = Column(Float)


# =========================
# KMS PILLARS
# =========================
class KMSPillar(Base):
    __tablename__ = "kms_pillars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dimension_id = Column(UUID(as_uuid=True), ForeignKey("kms_dimensions.id"))
    code = Column(String, unique=True)
    name = Column(String)
    description = Column(Text)
    qcb_references = Column(JSONB)
    order_index = Column(Integer)


# =========================
# KMS VARIABLES
# =========================
class KMSVariable(Base):
    __tablename__ = "kms_variables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pillar_id = Column(UUID(as_uuid=True), ForeignKey("kms_pillars.id"))
    name = Column(String)
    description = Column(Text)
    behavioral_indicators = Column(JSONB)
    weight = Column(Float)
    order_index = Column(Integer)


# =========================
# KMS PROFILE
# =========================
class KMSProfile(Base):
    __tablename__ = "kms_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))

    karakter_score = Column(Float)
    mental_score = Column(Float)
    softskill_score = Column(Float)
    overall_score = Column(Float)

    report_count = Column(Integer)
    last_updated = Column(DateTime)


# =========================
# PROFILE VARIABLE
# =========================
class KMSProfileVariable(Base):
    __tablename__ = "kms_profile_variables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kms_profile_id = Column(UUID(as_uuid=True), ForeignKey("kms_profiles.id"))
    kms_variable_id = Column(UUID(as_uuid=True), ForeignKey("kms_variables.id"))

    cumulative_score = Column(Float)
    data_point_count = Column(Integer)
    last_score = Column(Float)
    trend = Column(ENUM(TrendDirection, name="trend_direction"))
    updated_at = Column(DateTime)


# =========================
# TREATMENTS
# =========================
class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("santri.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    kms_variable_id = Column(UUID(as_uuid=True), ForeignKey("kms_variables.id"))
    generated_from_report = Column(UUID(as_uuid=True), ForeignKey("reports.id"))

    recommendation = Column(Text)
    priority = Column(ENUM(PriorityLevel, name="priority_level"))
    status = Column(String)
    musyrif_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# =========================
# EMBEDDINGS
# =========================
class KMSKnowledgeEmbedding(Base):
    __tablename__ = "kms_knowledge_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kms_variable_id = Column(UUID(as_uuid=True), ForeignKey("kms_variables.id"))
    content_type = Column(String)
    content_text = Column(Text)
    embedding = Column(Text)
    metadata_ = Column(JSONB)