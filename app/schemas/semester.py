
from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID

class SemesterBase(BaseModel):
    name: str
    academic_year: Optional[str] = None
    semester_number: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True

class SemesterCreate(SemesterBase):
    pass

class SemesterResponse(SemesterBase):
    id: UUID

    class Config:
        from_attributes = True
