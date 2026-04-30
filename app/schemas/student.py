from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID

class StudentBase(BaseModel):
    nis: str
    name: str
    kelas: str
    angkatan: int
    birth_info: Optional[str] = None
    address: Optional[str] = None
    guardian_name: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    musyrif_id: Optional[UUID] = None
    is_active: bool = True

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    nis: Optional[str] = None
    name: Optional[str] = None
    kelas: Optional[str] = None
    angkatan: Optional[int] = None
    birth_info: Optional[str] = None
    address: Optional[str] = None
    guardian_name: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    musyrif_id: Optional[UUID] = None
    is_active: Optional[bool] = None

class StudentResponse(StudentBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
