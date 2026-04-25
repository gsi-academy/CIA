from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

# ================= KMS PARAMETER =================
class KMSParamBase(BaseModel):
    category: str
    theme: str
    name: str
    description: str

class KMSParamCreate(KMSParamBase):
    pass

class KMSParamResponse(KMSParamBase):
    id: UUID

    class Config:
        from_attributes = True

# ================= STUDENT ACHIEVEMENT =================
class AchievementBase(BaseModel):
    santri_id: UUID
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
    santri_id: UUID
    semester_id: UUID
    karakter_score: float
    mental_score: float
    softskill_score: float
    overall_score: float
    report_count: int
    last_updated: datetime

    class Config:
        from_attributes = True
