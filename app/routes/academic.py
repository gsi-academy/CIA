from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from uuid import UUID
from typing import List

from app.database import get_db
from app.models.models import AcademicClass, ClassStudent, Student, StudentGrade

from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/academic", tags=["Academic"])


# ================= SCHEMA =================

class GradeItem(BaseModel):
    studentId: UUID
    nh: float
    nb: float
    na: float


class GradePayload(BaseModel):
    semesterId: UUID
    classId: UUID
    grades: List[GradeItem]


# ================= GET CLASSES =================

@router.get("/semesters/{semester_id}/classes")
def get_classes(
    semester_id: UUID,
    db: Session = Depends(get_db),
    user = None
):
    return db.query(AcademicClass).filter(
        AcademicClass.semester_id == semester_id
    ).all()


# ================= GET STUDENTS =================

@router.get("/classes/{class_id}/students")
def get_students(
    class_id: UUID,
    db: Session = Depends(get_db),
    user = None
):
    students = (
        db.query(Student)
        .join(ClassStudent, ClassStudent.student_id == Student.id)
        .filter(ClassStudent.class_id == class_id)
        .all()
    )
    return students


# ================= UPSERT GRADES =================

@router.post("/grades/upsert")
def upsert_grades(
    payload: GradePayload,
    db: Session = Depends(get_db),
    user = None
):
    for g in payload.grades:
        stmt = insert(StudentGrade).values(
            student_id=g.studentId,
            class_id=payload.classId,
            semester_id=payload.semesterId,
            nh=g.nh,
            nb=g.nb,
            na=g.na
        ).on_conflict_do_update(
            index_elements=["student_id", "class_id", "semester_id"],
            set_={
                "nh": g.nh,
                "nb": g.nb,
                "na": g.na
            }
        )

        db.execute(stmt)

    db.commit()

    return {"message": "Grades upserted successfully"}