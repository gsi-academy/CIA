import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE student_achievements DROP CONSTRAINT IF EXISTS student_achievements_parameter_id_fkey;"))
        # Hapus baris yang tidak ada di kms_main_indicators
        conn.execute(text("""
            DELETE FROM student_achievements 
            WHERE parameter_id NOT IN (SELECT id FROM kms_main_indicators);
        """))
        conn.execute(text("ALTER TABLE student_achievements ADD CONSTRAINT student_achievements_parameter_id_fkey FOREIGN KEY (parameter_id) REFERENCES kms_main_indicators(id) ON DELETE CASCADE;"))
        conn.commit()
        print("Success repairing FK on student_achievements")
    except Exception as e:
        print("Error:", e)
