"""
Script migrasi: menambahkan kolom phone, nip, unit ke tabel users.
Jalankan sekali: python migrate_add_profile_fields.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL tidak ditemukan di .env")

engine = create_engine(DATABASE_URL)

MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS nip VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS unit VARCHAR",
]

with engine.connect() as conn:
    for sql in MIGRATIONS:
        print(f"Menjalankan: {sql}")
        conn.execute(text(sql))
    conn.commit()

print("\n✅ Migrasi selesai! Kolom phone, nip, unit berhasil ditambahkan ke tabel users.")
