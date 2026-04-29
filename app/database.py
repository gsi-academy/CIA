from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load isi file .env
load_dotenv()

# Ambil URL database dari .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Buat koneksi ke PostgreSQL
engine = create_engine(DATABASE_URL)

# Session untuk komunikasi ke database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class untuk semua model
Base = declarative_base()

# Dependency untuk ambil DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()