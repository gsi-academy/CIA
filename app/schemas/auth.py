from pydantic import BaseModel, EmailStr
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