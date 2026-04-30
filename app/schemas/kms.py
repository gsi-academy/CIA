from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# ================= KMS DETAIL INDICATOR =================
class KMSDetailResponse(BaseModel):
    id: UUID
    indicator_detail: str
    action_template: Optional[str] = None  # Panduan tindakan musyrif

    class Config:
        from_attributes = True

class KMSDetailCreate(BaseModel):
    indicator_detail: str
    action_template: Optional[str] = None  # Opsional: override template otomatis

# ================= KMS MAIN INDICATOR =================
class KMSIndicatorBase(BaseModel):
    category: str
    name: str
    description: str
    theme: Optional[str] = "General"
    weight: Optional[float] = 1.0

class KMSIndicatorCreate(KMSIndicatorBase):
    pass

class KMSIndicatorResponse(KMSIndicatorBase):
    id: UUID
    details: List[KMSDetailResponse] = []

    class Config:
        from_attributes = True

# Alias lama untuk backward-compat internal (hapus setelah migrasi penuh)
KMSParamCreate = KMSIndicatorCreate
KMSParamResponse = KMSIndicatorResponse

# ================= STUDENT ACHIEVEMENT =================
class AchievementBase(BaseModel):
    student_id: UUID
    parameter_id: UUID
    status: str = "undefined"
    evidence_excerpt: Optional[str] = None

class AchievementResponse(AchievementBase):
    id: UUID
    last_updated: datetime

    class Config:
        from_attributes = True

# ================= KMS PROFILE =================
class KMSProfileResponse(BaseModel):
    id: UUID
    student_id: UUID
    semester_id: UUID
    karakter_score: float
    mental_score: float
    softskill_score: float
    overall_score: float
    report_count: int
    last_updated: datetime

    class Config:
        from_attributes = True
