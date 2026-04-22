# models_v2.py

import uuid
from sqlalchemy import Column, String, Integer, Text, Date, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


# ================= USERS =================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(Integer)  # 0 admin, 1 musyrif
    created_at = Column(TIMESTAMP)


# ================= STUDENTS =================
class Student(Base):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nis = Column(String, unique=True)
    name = Column(String)
    kelas = Column(String)
    angkatan = Column(Integer)
    created_at = Column(TIMESTAMP)


# ================= SEMESTERS =================
class Semester(Base):
    __tablename__ = "semesters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)


# ================= OBSERVATION =================
class ObservationDomain(Base):
    __tablename__ = "observation_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    musyrif_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))

    start_date = Column(Date)
    end_date = Column(Date)


# ================= MASTER =================
class CharMaster(Base):
    __tablename__ = "char_master"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    description = Column(Text)


class MentalMaster(Base):
    __tablename__ = "mental_master"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    description = Column(Text)


class SoftskillMaster(Base):
    __tablename__ = "softskill_master"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    description = Column(Text)


# ================= REPORT =================
class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    musyrif_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))

    report_date = Column(Date)
    transcript = Column(Text)
    status = Column(String)

    created_at = Column(TIMESTAMP)


# ================= ANALYSIS =================
class ReportAnalysis(Base):
    __tablename__ = "report_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))

    insight = Column(Text)
    recommendation = Column(Text)

    created_at = Column(TIMESTAMP)


# ================= STATUS TABLES =================
class ReportCharStatus(Base):
    __tablename__ = "report_char_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    char_id = Column(UUID(as_uuid=True), ForeignKey("char_master.id"))

    status = Column(String)
    evidence = Column(Text)


class ReportMentalStatus(Base):
    __tablename__ = "report_mental_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    mental_id = Column(UUID(as_uuid=True), ForeignKey("mental_master.id"))

    status = Column(String)
    evidence = Column(Text)


class ReportSoftskillStatus(Base):
    __tablename__ = "report_softskill_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    softskill_id = Column(UUID(as_uuid=True), ForeignKey("softskill_master.id"))

    status = Column(String)
    evidence = Column(Text)


# ================= AGGREGATION =================
class StudentChar(Base):
    __tablename__ = "student_char"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    char_id = Column(UUID(as_uuid=True), ForeignKey("char_master.id"))

    status = Column(String)
    last_updated = Column(TIMESTAMP)


class StudentMental(Base):
    __tablename__ = "student_mental"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    mental_id = Column(UUID(as_uuid=True), ForeignKey("mental_master.id"))

    status = Column(String)
    last_updated = Column(TIMESTAMP)


class StudentSoftskill(Base):
    __tablename__ = "student_softskill"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    softskill_id = Column(UUID(as_uuid=True), ForeignKey("softskill_master.id"))

    status = Column(String)
    last_updated = Column(TIMESTAMP)


# ================= PROFILING =================
class Profiling(Base):
    __tablename__ = "profiling"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    santri_id = Column(UUID(as_uuid=True), ForeignKey("students.id"))
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))

    insight = Column(Text)
    recommendation = Column(Text)

    dominant_positive = Column(String)
    dominant_negative = Column(String)

    created_at = Column(TIMESTAMP)