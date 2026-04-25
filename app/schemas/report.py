from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class ReportSubmit(BaseModel):
    santri_id: str
    semester_id: str
    transcript: str = Field(..., min_length=10)


class ReportVerify(BaseModel):
    text: Optional[str] = None


class ReportResponse(BaseModel):
    message: str
    report_id: str


class DetectionResponse(BaseModel):
    parameter_id: UUID
    status_detected: str
    evidence: str

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: UUID
    report_id: UUID
    insight: Optional[str] = None
    recommendation: Optional[str] = None
    detections: List[DetectionResponse] = []

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    santri_id: str
    total_reports: int
    average_score: float
    trend: str
    alert: Optional[str]
    detail_scores: dict


class ExportResponse(BaseModel):
    santri: dict
    summary: dict
    treatments: list