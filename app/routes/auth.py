from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.database import SessionLocal
# <<<<<<< HEAD
from app.models.models_v2 import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import hash_password, verify_password, create_access_token

from app.models.models import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse, UserUpdate
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
# >>>>>>> 8a27fec0e74a8bdca7b3181358ed382b304ef6c8

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# =========================
# DEPENDENCY DB
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token tidak valid atau sudah kadaluarsa.")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan.")
    return user


# =========================
# REGISTER
# =========================
@router.post("/register", response_model=TokenResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):

    # cek email sudah ada atau belum
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # hash password
    hashed_password = hash_password(user.password)

    # buat user baru dengan role 1 (musyrif biasa) sebagai default
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        role=user.role if user.role in [0, 1] else 1
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # buat token
    token = create_access_token({"sub": str(new_user.id), "role": new_user.role})

    return {"access_token": token}


# =========================
# LOGIN
# =========================
@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    db_user = db.query(User).filter(User.email == form_data.username).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if db_user.role not in [0, 1]:
        raise HTTPException(
            status_code=400,
            detail="Data role tidak valid (harus 0 atau 1). Silakan reset database."
        )

    if not verify_password(form_data.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_access_token({
        "sub": str(db_user.id),
        "role": db_user.role
    })

    return {"access_token": token}


# =========================
# ME (cek session aktif)
# =========================
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "phone": current_user.phone,
        "nip": current_user.nip,
        "unit": current_user.unit,
        "created_at": str(current_user.created_at),
    }


# =========================
# UPDATE PROFILE (PATCH /auth/me)
# =========================
@router.patch("/me")
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.name is not None:
        current_user.name = payload.name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.nip is not None:
        current_user.nip = payload.nip
    if payload.unit is not None:
        current_user.unit = payload.unit

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "phone": current_user.phone,
        "nip": current_user.nip,
        "unit": current_user.unit,
        "created_at": str(current_user.created_at),
    }