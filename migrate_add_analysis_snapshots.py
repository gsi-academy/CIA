"""
Migrasi: Tambah tabel student_analysis_snapshots dan snapshot_detections.
Jalankan sekali: python migrate_add_analysis_snapshots.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Tabel utama: student_analysis_snapshots
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS student_analysis_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            santri_id UUID REFERENCES santri(id) ON DELETE CASCADE,
            semester_id UUID REFERENCES semesters(id),
            performed_by UUID REFERENCES users(id),
            performed_at TIMESTAMP DEFAULT NOW(),

            reports_included INTEGER DEFAULT 0,
            analyzed_up_to TIMESTAMP,

            karakter_score FLOAT DEFAULT 0,
            mental_score FLOAT DEFAULT 0,
            softskill_score FLOAT DEFAULT 0,
            overall_score FLOAT DEFAULT 0,

            karakter_achieved INTEGER DEFAULT 0,
            karakter_total INTEGER DEFAULT 0,
            mental_achieved INTEGER DEFAULT 0,
            mental_total INTEGER DEFAULT 0,
            softskill_achieved INTEGER DEFAULT 0,
            softskill_total INTEGER DEFAULT 0,

            insight TEXT,
            treatment_k TEXT,
            treatment_m TEXT,
            treatment_s TEXT
        );
    """))

    # Tabel deteksi per snapshot
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS snapshot_detections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            snapshot_id UUID REFERENCES student_analysis_snapshots(id) ON DELETE CASCADE,
            main_indicator_id UUID REFERENCES kms_main_indicators(id),
            detail_indicator_id UUID REFERENCES kms_detail_indicators(id),
            evidence_excerpt TEXT
        );
    """))

    conn.commit()
    print("✅ Tabel student_analysis_snapshots dan snapshot_detections berhasil dibuat.")
