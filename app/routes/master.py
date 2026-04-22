from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models_v2 import Student, Semester
from pydantic import BaseModel
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/master", tags=["Master Data"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =========================
# DB SESSION
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# AUTH
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)

    # hanya admin (role = 0)
    if payload["role"] != 0:
        raise HTTPException(status_code=403, detail="Admin only")

    return payload


# =========================
# SCHEMAS
# =========================
class SantriCreate(BaseModel):
    nis: str
    name: str
    angkatan: int
    kelas: str


class SemesterCreate(BaseModel):
    name: str
    academic_year: str
    semester_number: int


# =========================
# SANTRI CRUD
# =========================
@router.get("/santri")
def get_santri(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Santri).all()


@router.post("/santri")
def create_santri(data: SantriCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):

    santri = Santri(**data.dict())
    db.add(santri)
    db.commit()
    db.refresh(santri)

    return santri


@router.put("/santri/{santri_id}")
def update_santri(
    santri_id: str,
    data: SantriCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    santri = db.query(Santri).filter(Santri.id == santri_id).first()

    if not santri:
        raise HTTPException(status_code=404, detail="Not found")

    for key, value in data.dict().items():
        setattr(santri, key, value)

    db.commit()

    return santri


@router.delete("/santri/{santri_id}")
def delete_santri(
    santri_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    santri = db.query(Santri).filter(Santri.id == santri_id).first()

    if not santri:
        raise HTTPException(status_code=404, detail="Not found")

    db.delete(santri)
    db.commit()

    return {"message": "deleted"}


# =========================
# SEMESTER CRUD
# =========================
@router.get("/semesters")
def get_semesters(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Semester).all()


@router.post("/semesters")
def create_semester(data: SemesterCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):

    semester = Semester(**data.dict())
    db.add(semester)
    db.commit()
    db.refresh(semester)

    return semester