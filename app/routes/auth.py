from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

# =========================
# DEPENDENCY DB
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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

    # buat user baru
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # buat token
    token = create_access_token({"sub": str(new_user.id), "role": new_user.role})

    return {"access_token": token}


# =========================
# LOGIN (FIX SWAGGER)
# =========================
@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    db_user = db.query(User).filter(User.email == form_data.username).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # 🔥 VALIDASI ROLE KOTOR
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