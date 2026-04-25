from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID

class SantriBase(BaseModel):
    nis: str
    name: str
    kelas: str
    angkatan: int
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    photo_url: Optional[str] = None
    is_active: bool = True

class SantriCreate(SantriBase):
    pass

class SantriUpdate(BaseModel):
    nis: Optional[str] = None
    name: Optional[str] = None
    kelas: Optional[str] = None
    angkatan: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    photo_url: Optional[str] = None
    is_active: Optional[bool] = None

class SantriResponse(SantriBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
