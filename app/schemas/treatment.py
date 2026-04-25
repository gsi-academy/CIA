from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class TreatmentBase(BaseModel):
    santri_id: UUID
    semester_id: UUID
    generated_from_report: Optional[UUID] = None
    recommendation: str
    priority: str = "medium"
    status: str = "pending"
    musyrif_notes: Optional[str] = None

class TreatmentCreate(TreatmentBase):
    pass

class TreatmentUpdate(BaseModel):
    recommendation: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    musyrif_notes: Optional[str] = None

class TreatmentResponse(TreatmentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
