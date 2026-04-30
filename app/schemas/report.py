from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class ReportSubmit(BaseModel):
    student_id: str
    semester_id: str
    transcript: str
    run_analysis: bool = False


class ReportVerify(BaseModel):
    text: str


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
    student_id: str
    total_reports: int
    average_score: float
    trend: str
    alert: Optional[str]
    detail_scores: dict


class ExportResponse(BaseModel):
    student: dict
    summary: dict
    treatments: list