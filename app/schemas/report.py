from pydantic import BaseModel, Field
from typing import Optional

class ReportSubmit(BaseModel):
    santri_id: str
    semester_id: str
    transcript: str = Field(..., min_length=10)


class ReportResponse(BaseModel):
    message: str
    report_id: str

class DashboardResponse(BaseModel):
    santri_id: str
    total_reports: int
    average_score: float
    trend: str
    alert: Optional[str]


class ExportResponse(BaseModel):
    santri: dict
    summary: dict
    treatments: list