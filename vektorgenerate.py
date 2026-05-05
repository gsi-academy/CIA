import os
import pandas as pd
import uuid
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Load Environment
load_dotenv()

# Ambil API Key & DB Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "cia_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "admin"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

DATASET_DIR = "dataset"

# FIX: Inisialisasi client OpenAI dengan benar
client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text):
    """Fungsi generate embedding"""
    text = text.replace("\n", " ")
    # Di sini error-nya tadi, sekarang sudah fix manggil objek client
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def find_column(df, keywords):
    """Cari nama kolom otomatis"""
    for col in df.columns:
        if any(key.lower() in col.lower() for key in keywords):
            return col
    return None

def process_and_sync():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ Terhubung ke PostgreSQL.")
        
        # Kosongkan data lama
        print("🧹 Membersihkan database...")
        cur.execute("TRUNCATE TABLE knowledge_base RESTART IDENTITY;")
        conn.commit()
    except Exception as e:
        print(f"❌ Gagal konek/bersihkan Database: {e}")
        return

    # Mapping File
    pillars = [
        {"main": "mental.csv", "detail": "mental_micro.csv", "name": "Mental"},
        {"main": "character.csv", "detail": "character_micro.csv", "name": "Karakter"},
        {"main": "softskill.csv", "detail": "softskill_micro.csv", "name": "Softskill"}
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " "]
    )

    print("🚀 Memulai proses sinkronisasi...")

    for p in pillars:
        main_path = os.path.join(DATASET_DIR, p['main'])
        detail_path = os.path.join(DATASET_DIR, p['detail'])

        if not os.path.exists(main_path):
            print(f"⚠️ Skip {p['name']}: File {main_path} tidak ditemukan.")
            continue

        print(f"📦 Processing Pilar: {p['name']}...")
        df_main = pd.read_csv(main_path)
        df_detail = pd.read_csv(detail_path)

        # Deteksi Kolom
        main_id_col = find_column(df_main, ['id', 'no'])
        detail_rel_col = find_column(df_detail, ['id', p['name']])
        detail_text_col = find_column(df_detail, ['indikator', 'detail', 'micro'])
        judul_col = find_column(df_main, [p['name'], 'judul', 'nama'])
        desc_col = find_column(df_main, ['penjelasan', 'deskripsi'])

        for _, row in df_main.iterrows():
            try:
                id_val = row[main_id_col]
                sub_details = df_detail[df_detail[detail_rel_col] == id_val][detail_text_col].tolist()
                
                judul = row.get(judul_col, 'N/A')
                penjelasan = row.get(desc_col, '')

                full_text = f"PILAR: {p['name']}\nJUDUL: {judul}\n"
                full_text += f"PENJELASAN: {penjelasan}\nDETAIL INDIKATOR:\n- " + "\n- ".join([str(d) for d in sub_details])

                chunks = splitter.split_text(full_text)

                for chunk in chunks:
                    vector = get_embedding(chunk)
                    cur.execute("""
                        INSERT INTO knowledge_base (id, content, embedding, pilar, original_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (str(uuid.uuid4()), chunk, vector, p['name'], str(id_val)))
                
                conn.commit()
            except Exception as row_error:
                conn.rollback()
                print(f"❌ Error ID {row.get(main_id_col)}: {row_error}")

    cur.close()
    conn.close()
    print("🏁 SELESAI! Data sudah masuk ke pgvector.")

if __name__ == "__main__":
    process_and_sync()