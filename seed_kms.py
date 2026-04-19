import uuid
from datetime import date
from app.database import SessionLocal
from app.models.models import (
    KMSDimension, KMSPillar, KMSVariable, KMSCode, 
    Santri, Semester
)

db = SessionLocal()

def seed():
    print("Memulai proses seeding...")

    # =========================
    # 1. SEED SEMESTER (PENTING UNTUK TEST)
    # =========================
    semester_ganjil = Semester(
        id=uuid.uuid4(),
        name="Semester Ganjil 2025/2026",
        academic_year="2025/2026",
        semester_number=1,
        is_active=True
    )
    db.add(semester_ganjil)
    print("✅ Semester ditambahkan")

    # =========================
    # 2. SEED SANTRI (PENTING UNTUK TEST)
    # =========================
    santri_list = [
        Santri(
            id=uuid.uuid4(),
            nis="12345",
            name="Fatih Al-Fatih",
            date_of_birth=date(2010, 5, 20),
            gender="Laki-laki",
            angkatan=2025,
            kelas="10-A"
        ),
        Santri(
            id=uuid.uuid4(),
            nis="12346",
            name="Kenan Ahmad",
            date_of_birth=date(2010, 8, 12),
            gender="Laki-laki",
            angkatan=2025,
            kelas="10-B"
        )
    ]
    db.add_all(santri_list)
    print("✅ Data Santri ditambahkan")

    # =========================
    # 3. DIMENSIONS
    # =========================
    karakter = KMSDimension(
        id=uuid.uuid4(),
        code=KMSCode.K,
        name="Karakter",
        weight=0.4
    )
    mental = KMSDimension(
        id=uuid.uuid4(),
        code=KMSCode.M,
        name="Mental",
        weight=0.3
    )
    softskill = KMSDimension(
        id=uuid.uuid4(),
        code=KMSCode.S,
        name="Soft Skill",
        weight=0.3
    )
    db.add_all([karakter, mental, softskill])
    db.commit() # Commit dulu biar ID Dimensi bisa dipakai pilar

    # =========================
    # 4. PILAR (CONTOH)
    # =========================
    # Karakter K1 - K8
    karakter_pillars = []
    for i in range(1, 9):
        p = KMSPillar(
            id=uuid.uuid4(),
            dimension_id=karakter.id,
            code=f"K{i}",
            name=f"Pilar Karakter {i}",
            order_index=i
        )
        karakter_pillars.append(p)
    
    db.add_all(karakter_pillars)
    db.commit()

    print(f"\n🚀 SEEDING SELESAI!")
    print(f"Gunakan ID ini untuk tes di Postman:")
    print(f"ID Semester: {semester_ganjil.id}")
    print(f"ID Santri 1: {santri_list[0].id} ({santri_list[0].name})")
    print(f"ID Santri 2: {santri_list[1].id} ({santri_list[1].name})")

if __name__ == "__main__":
    try:
        seed()
    except Exception as e:
        print(f"❌ Error saat seeding: {e}")
        db.rollback()
    finally:
        db.close()