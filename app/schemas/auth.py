from typing import Optional
from pydantic import BaseModel, EmailStr, Field

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
    id: str
    name: str
    email: str
    role: int
    phone: Optional[str] = None
    nip: Optional[str] = None
    unit: Optional[str] = None
    created_at: str

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