"""
migrate_action_template.py
Tambah kolom action_template ke kms_detail_indicators,
lalu auto-generate nilainya berdasarkan nama indikator & kategori parent.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

def generate_action(indicator_detail: str, main_name: str, category: str) -> str:
    """
    Generate kalimat panduan tindakan musyrif secara otomatis.
    Diarahkan kepada musyrif (bukan santri), konkret, dan actionable.
    """
    cat_ctx = {
        "karakter": "Karakter",
        "mental": "Mental & Spiritual",
        "softskill": "Softskill & Sosial",
    }.get(category, "Kompetensi")

    templates = [
        f"Dalam aspek {cat_ctx} — indikator '{main_name}': dorong santri untuk {indicator_detail.lower().rstrip('.')} dengan memberikan contoh nyata dan penguatan positif secara konsisten.",
    ]

    return templates[0]


with engine.connect() as conn:
    # 1. Tambah kolom (idempotent: IF NOT EXISTS)
    try:
        conn.execute(text(
            "ALTER TABLE kms_detail_indicators ADD COLUMN IF NOT EXISTS action_template TEXT;"
        ))
        conn.commit()
        print("[OK] Kolom action_template ditambahkan (atau sudah ada).")
    except Exception as e:
        print(f"[ERROR] Gagal menambah kolom: {e}")
        raise

    # 2. Ambil semua detail yang belum punya action_template
    rows = conn.execute(text("""
        SELECT 
            d.id,
            d.indicator_detail,
            m.name AS main_name,
            m.category
        FROM kms_detail_indicators d
        JOIN kms_main_indicators m ON d.main_indicator_id = m.id
        WHERE d.action_template IS NULL OR d.action_template = ''
    """)).fetchall()

    print(f"-> {len(rows)} baris perlu di-generate action_template-nya...")

    # 3. Update satu per satu
    updated = 0
    for row in rows:
        action = generate_action(
            indicator_detail=row.indicator_detail,
            main_name=row.main_name,
            category=row.category
        )
        conn.execute(
            text("UPDATE kms_detail_indicators SET action_template = :action WHERE id = :id"),
            {"action": action, "id": row.id}
        )
        updated += 1

    conn.commit()
    print(f"[OK] {updated} action_template berhasil di-generate dan disimpan.")
    print("Migration selesai.")
