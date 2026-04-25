import os
import json

# Dummy AI Engine untuk testing tanpa API Key OpenAI
def analyze_report(transcript: str):
    """
    Mengembalikan simulasi deteksi parameter KMS.
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