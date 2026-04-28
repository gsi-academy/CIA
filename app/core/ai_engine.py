import os
import json

# ===========================================================================
# ANALYZE REPORT
# Mendeteksi indikator KMS dari transkrip laporan musyrif.
# ===========================================================================
def analyze_report(transcript: str) -> dict:
    """
    Mengembalikan simulasi deteksi parameter KMS.
    Ganti implementasi ini dengan pemanggilan LLM sungguhan.
    """
    dummy_result = {
        "detections": [
            {
                "parameter_name": "Memiliki tujuan hidup",
                "category": "karakter",
                "status": "gained",
                "evidence": "Santri menyatakan ingin menjadi Hafiz agar bisa bermanfaat bagi umat."
            },
            {
                "parameter_name": "Prinsip belajar",
                "category": "mental",
                "status": "gained",
                "evidence": "Santri belajar dengan tekun di kelas dan mencoba memahami materi secara mendalam."
            },
            {
                "parameter_name": "Keinginan untuk selalu mengembangkan diri.",
                "category": "softskill",
                "status": "gained",
                "evidence": "Santri bertanya tentang materi tambahan di luar jam pelajaran."
            }
        ],
        "insight": "Santri menunjukkan motivasi belajar yang tinggi dan kesadaran akan tujuan hidupnya. Perkembangan kognitif dan emotionalnya sangat stabil.",
        "recommendation": "Berikan apresiasi atas kemajuannya dan tantangan baru dalam hafalan agar terus berkembang."
    }
    return dummy_result


# ===========================================================================
# GENERATE TREATMENT
# Generate panduan tindakan musyrif yang dipersonalisasi berdasarkan:
#   - transcript: isi laporan santri (konteks kondisi santri)
#   - unachieved_per_cat: indikator yang belum tercapai per kategori K/M/S
#
# Return format:
#   {
#     "karakter": ["action string 1", "action string 2", ...],
#     "mental":   ["action string 1", ...],
#     "softskill": [...]
#   }
#
# CATATAN UNTUK INTEGRASI AI:
#   Ganti isi fungsi ini dengan pemanggilan LLM (OpenAI, Gemini, dsb).
#   Kirim transcript + daftar unachieved indicators sebagai prompt,
#   lalu parse response AI ke format list string per kategori.
# ===========================================================================
def generate_treatment(transcript: str, unachieved_per_cat: dict) -> dict:
    """
    Generate kalimat panduan tindakan musyrif yang dipersonalisasi per analisis.
    Dummy ini menghasilkan kalimat yang terlihat cerdas dan kontekstual.
    """
    # Deteksi sentimen sederhana dari transcript untuk variasi kalimat
    is_positive = any(word in transcript.lower() for word in ["baik", "rajin", "lancar", "alhamdulillah", "bagus"])
    tone = "Pertahankan momentum positif santri." if is_positive else "Berikan dukungan ekstra karena santri sedang menghadapi hambatan."

    result = {}
    for cat, items in unachieved_per_cat.items():
        actions = []
        for item in items:
            # Variasi kalimat berdasarkan kategori
            if cat == "karakter":
                action = f"Gunakan pendekatan personal untuk menguatkan aspek '{item['main_name']}'. {tone} Ajarkan santri cara {item['detail_text'].lower()} melalui keteladanan harian di asrama."
            elif cat == "mental":
                action = f"Fokus pada penguatan spiritualitas terkait '{item['main_name']}'. Musyrif disarankan mengajak santri melakukan {item['detail_text'].lower()} secara rutin sebagai bagian dari riyadhah."
            else: # softskill
                action = f"Berikan ruang bagi santri untuk mempraktikkan '{item['main_name']}'. Tantang santri untuk menunjukkan kemampuan {item['detail_text'].lower()} dalam kegiatan kelompok minggu ini."
            
            actions.append(action)
        result[cat] = actions

    return result