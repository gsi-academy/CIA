import os
import pandas as pd
import uuid
import psycopg2
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

# === CONFIGURATION ===
OPENAI_API_KEY = ("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")
DB_CONFIG = {
    "dbname": "cia_db",
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
}

DATASET_DIR = "dataset"
client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text):
    text = text.replace("\n", " ")
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def find_column(df, keywords):
    """Fungsi pembantu buat nyari kolom berdasarkan kata kunci (case-insensitive)"""
    for col in df.columns:
        if any(key.lower() in col.lower() for key in keywords):
            return col
    return None

def process_and_sync():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Gagal konek ke Database: {e}")
        return

    # Update nama file sesuai file yang lu kasih
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

    print("🚀 Memulai proses sinkronisasi ke PostgreSQL...")

    for p in pillars:
        main_path = os.path.join(DATASET_DIR, p['main'])
        detail_path = os.path.join(DATASET_DIR, p['detail'])

        if not os.path.exists(main_path) or not os.path.exists(detail_path):
            print(f"⚠️ Skip {p['name']}: File {main_path} atau {detail_path} tidak ditemukan.")
            continue

        print(f"📦 Processing Pilar: {p['name']}...")
        df_main = pd.read_csv(main_path)
        df_detail = pd.read_csv(detail_path)

        # Mapping kolom secara otomatis
        main_id_col = find_column(df_main, ['id'])
        # Cari kolom relasi di file detail (yang mengandung 'id' tapi bukan kolom 'id' utama detail)
        detail_rel_col = next((c for c in df_detail.columns if 'id' in c.lower() and c.lower() != 'id'), df_detail.columns[0])
        detail_text_col = find_column(df_detail, ['indikator', 'detail', 'micro'])
        tema_col = find_column(df_main, ['tema', 'pilar'])
        penjelasan_col = find_column(df_main, ['penjelasan', 'deskripsi'])

        for _, row in df_main.iterrows():
            try:
                # Ambil detail indikator
                sub_details = df_detail[df_detail[detail_rel_col] == row[main_id_col]][detail_text_col].tolist()
                
                # Coba cari judul dari berbagai kemungkinan nama kolom
                judul = row.get('Mental') or row.get('Karakter') or row.get('Softskill') or row.get('judul') or 'N/A'
                tema = row.get(tema_col, p['name'])
                penjelasan = row.get(penjelasan_col, '')

                full_text = f"PILAR: {p['name']}\nTEMA: {tema}\nJUDUL: {judul}\n"
                full_text += f"PENJELASAN: {penjelasan}\nDETAIL INDIKATOR:\n- " + "\n- ".join([str(d) for d in sub_details])

                chunks = splitter.split_text(full_text)

                for chunk in chunks:
                    vector = get_embedding(chunk)
                    query = """
                        INSERT INTO knowledge_base (id, content, embedding, pilar, tema, original_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(query, (
                        str(uuid.uuid4()),
                        chunk,
                        vector,
                        p['name'],
                        str(tema),
                        int(row[main_id_col])
                    ))
                
                conn.commit()
            except Exception as row_error:
                conn.rollback()
                print(f"❌ Error baris ID {row.get(main_id_col)} di {p['name']}: {row_error}")

        print(f"✅ Pilar {p['name']} selesai disinkronisasi.")

    cur.close()
    conn.close()
    print("🏁 Semua data berhasil masuk ke database pgvector!")

if __name__ == "__main__":
    process_and_sync()