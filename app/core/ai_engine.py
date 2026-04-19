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
  "karakter_score": 0-100,
  "mental_score": 0-100,
  "softskill_score": 0-100,
  "analysis": "penjelasan singkat",
  "recommendation": "saran tindakan untuk musyrif (1-2 kalimat)"
}

Aturan:
- JSON saja
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
        return result
    except:
        return {
            "karakter_score": 50,
            "mental_score": 50,
            "softskill_score": 50,
            "analysis": "fallback karena parsing gagal"
        }