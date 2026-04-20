import os
import json
from langchain_openai import ChatOpenAI

# =========================
# INIT LLM
# =========================
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.2
)

# =========================
# SYSTEM PROMPT (CORE LOGIC AI)
# =========================
SYSTEM_PROMPT = """
Kamu adalah pakar psikologi pendidikan santri.

Analisis teks laporan dan berikan output JSON:

{
  "karakter": {
    "score": 0-100,
    "evidence": "kutipan teks yang mendukung"
  },
  "mental": {
    "score": 0-100,
    "evidence": "kutipan teks yang mendukung"
  },
  "softskill": {
    "score": 0-100,
    "evidence": "kutipan teks yang mendukung"
  },
  "recommendation": "saran tindakan untuk musyrif (1-2 kalimat)"
}

Aturan:
- JSON saja
- Evidence HARUS kutipan dari teks
- Jika tidak jelas → skor 50
"""


# =========================
# MAIN FUNCTION
# =========================
def analyze_report(transcript: str):

    messages = [
        ("system", SYSTEM_PROMPT),
        ("user", transcript)
    ]

    response = llm.invoke(messages)

    try:
        result = json.loads(response.content)

        return {
            "karakter_score": result["karakter"]["score"],
            "mental_score": result["mental"]["score"],
            "softskill_score": result["softskill"]["score"],
            "evidence": {
                "karakter": result["karakter"]["evidence"],
                "mental": result["mental"]["evidence"],
                "softskill": result["softskill"]["evidence"]
            },
            "recommendation": result["recommendation"]
        }

    except:
        return {
            "karakter_score": 50,
            "mental_score": 50,
            "softskill_score": 50,
            "evidence": {},
            "recommendation": "Perlu observasi lebih lanjut"
        }