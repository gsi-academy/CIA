from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime

# =========================
# REGISTER
# =========================
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: int = Field(default=1, ge=0, le=1)  # hanya 0 atau 1

# =========================
# LOGIN
# =========================
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# =========================
# RESPONSE TOKEN
# =========================
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =========================
# RESPONSE USER (GET /auth/me)
# =========================
class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: int
    phone: Optional[str] = None
    nip: Optional[str] = None
    unit: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================
# UPDATE PROFILE (PATCH /auth/me)
# =========================
class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    nip: Optional[str] = None
    unit: Optional[str] = None


# =========================
# ADMIN: MUSYRIF CREATE
# =========================
class MusyrifCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    nip: Optional[str] = None
    unit: Optional[str] = None