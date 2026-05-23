import json
from typing import List, Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# ==========================================
# 1. PYDANTIC SCHEMAS (Untuk Output LLM)
# ==========================================

class Detection(BaseModel):
    detail_id: str = Field(description="ID unik dari indikator detail yang terdeteksi")
    evidence: str = Field(description="Kutipan persis dari transkrip yang menjadi bukti tercapainya indikator ini")

class DetectionResult(BaseModel):
    detections: List[Detection] = Field(default_factory=list, description="Daftar indikator detail yang ditemukan di teks")

class TreatmentAction(BaseModel):
    detail_id: str
    main_name: str
    detail_text: str
    action: str = Field(description="Saran tindakan spesifik untuk musyrif (maks 2 kalimat)")

class AIAction(BaseModel):
    detail_id: str = Field(description="ID detail_id dari indikator yang diberikan")
    action: str = Field(description="Saran tindakan spesifik untuk musyrif (maks 2 kalimat)")

class TreatmentResult(BaseModel):
    insight: str = Field(description="Ringkasan atau kesimpulan singkat dari perkembangan student")
    karakter_actions: List[AIAction] = Field(default_factory=list)
    mental_actions: List[AIAction] = Field(default_factory=list)
    softskill_actions: List[AIAction] = Field(default_factory=list)
# ==========================================
# 2. STATE GRAPH DEFINITION
# ==========================================

class KMSAnalysisState(TypedDict):
    # Input dari service
    transcript: str
    past_detected_detail_ids: List[str]
    all_main_indicators: List[Dict[str, Any]]   # id, name, category
    all_detail_indicators: List[Dict[str, Any]] # id, main_id, detail_text
    
    # State internal yang di-update oleh Nodes
    new_detections: List[Dict[str, str]]        # [{detail_id, evidence}]
    all_detected_detail_ids: set
    achieved_main_ids: set
    scores: Dict[str, Any]
    unachieved_targets: Dict[str, List[Dict[str, Any]]] # Max 3 per kategori untuk di-treatment
    
    # Output akhir
    insight: str
    treatments: Dict[str, List[Dict[str, Any]]] # karakter, mental, softskill


# Inisialisasi LLM (Pastikan variabel env OPENAI_API_KEY sudah di-set)
llm_detect = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_treatment = ChatOpenAI(model="gpt-4o", temperature=0.5)

# ==========================================
# 3. GRAPH NODES
# ==========================================

def detect_indicators_node(state: KMSAnalysisState):
    """
    Node 1: Mendeteksi indikator yang TERPENUHI dari laporan baru.
    Hanya mengecek indikator yang BELUM pernah terdeteksi sebelumnya.
    """
    transcript = state["transcript"]
    past_ids = set(state["past_detected_detail_ids"])
    
    # Filter indikator yang belum pernah tercapai
    pending_indicators = [
        ind for ind in state["all_detail_indicators"] 
        if ind["id"] not in past_ids
    ]
    
    # Jika transkrip kosong atau semua sudah tercapai, lewati.
    if not transcript.strip() or not pending_indicators:
        return {"new_detections": []}

    # Buat prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Kamu adalah AI analis psikologi pendidikan. Tugasmu mendeteksi apakah perilaku murid dalam laporan memenuhi indikator tertentu. "
                   "Hanya pilih indikator jika ada BUKTI KUAT di dalam teks laporan. Jika tidak ada, kembalikan list kosong."),
        ("user", "Transkrip Laporan:\n{transcript}\n\n"
                 "Daftar Indikator yang belum terpenuhi (JSON):\n{indicators}\n\n"
                 "Ekstrak indikator mana saja yang terdeteksi dan berikan bukti kutipannya.")
    ])
    
    chain = prompt | llm_detect.with_structured_output(DetectionResult)
    
    # Format indikator agar muat di prompt secara efisien
    indicators_json = json.dumps([
        {"id": ind["id"], "indikator": ind["detail_text"]} 
        for ind in pending_indicators
    ])
    
    result = chain.invoke({"transcript": transcript, "indicators": indicators_json})
    
    return {"new_detections": [d.model_dump() for d in result.detections]}


def calculate_metrics_node(state: KMSAnalysisState):
    """
    Node 2: Menghitung ulang KMS Score gabungan historis + baru, dan mencari unachieved targets.
    """
    new_dets = {d["detail_id"] for d in state.get("new_detections", [])}
    past_ids = set(state["past_detected_detail_ids"])
    all_detected_detail_ids = past_ids | new_dets
    
    # Cari main indicators mana yang sudah tercapai (minimal 1 detail terdeteksi)
    achieved_main_ids = set()
    for detail in state["all_detail_indicators"]:
        if detail["id"] in all_detected_detail_ids:
            achieved_main_ids.add(detail["main_id"])
            
    # Hitung skor
    scores = {}
    unachieved_targets = {"karakter": [], "mental": [], "softskill": []}
    
    for cat in ["karakter", "mental", "softskill"]:
        # Ambil main indicator berdasarkan kategori
        mains_in_cat = [m for m in state["all_main_indicators"] if m["category"] == cat]
        total = len(mains_in_cat) or 1
        achieved_list = [m for m in mains_in_cat if m["id"] in achieved_main_ids]
        achieved_count = len(achieved_list)
        
        scores[cat] = {
            "total": total,
            "achieved": achieved_count,
            "score": round((achieved_count / total) * 100, 1)
        }
        
        # Cari max 3 indikator untuk treatment (belum tercapai)
        cat_unachieved = []
        for main in mains_in_cat:
            if main["id"] not in achieved_main_ids:
                # Cari 1 detail perwakilan
                detail_rep = next((d for d in state["all_detail_indicators"] if d["main_id"] == main["id"]), None)
                if detail_rep:
                    cat_unachieved.append({
                        "main_id": main["id"],
                        "main_name": main["name"],
                        "detail_id": detail_rep["id"],
                        "detail_text": detail_rep["detail_text"]
                    })
            if len(cat_unachieved) >= 3:
                break
        unachieved_targets[cat] = cat_unachieved

    return {
        "all_detected_detail_ids": all_detected_detail_ids,
        "achieved_main_ids": achieved_main_ids,
        "scores": scores,
        "unachieved_targets": unachieved_targets
    }


def generate_insight_treatment_node(state: KMSAnalysisState):
    """
    Node 3: Menghasilkan Insight (feedback/summary) dan Action Plan (Saran Treatment).
    Python akan me-merge output AI dengan data indikator asli agar struktur 100% sama dengan dummy.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Kamu adalah konsultan pendamping asrama (musyrif). Tugasmu menyusun ringkasan perkembangan siswa (Insight) "
                   "berdasarkan skor dan laporan terbarunya, serta memberikan saran tindakan konkrit untuk indikator yang BELUM TERCAPAI. "
                   "Kembalikan detail_id yang sama persis beserta action-nya."),
        ("user", "Transkrip Laporan Baru:\n{transcript}\n\n"
                 "Skor KMS Saat Ini:\n{scores}\n\n"
                 "Target yang belum tercapai (perlu treatment):\n{unachieved}\n\n"
                 "Buat Insight ringkas dan treatment plan yang spesifik.")
    ])
    
    chain = prompt | llm_treatment.with_structured_output(TreatmentResult)
    result = chain.invoke({
        "transcript": state["transcript"],
        "scores": json.dumps(state["scores"]),
        "unachieved": json.dumps(state["unachieved_targets"])
    })
    
    # === PROSES MERGE PROGRAMMATIC (SEPERTI DUMMY) ===
    treatments = {"karakter": [], "mental": [], "softskill": []}
    
    # Mapping output AI ke dictionary untuk pencarian cepat
    ai_maps = {
        "karakter": {a.detail_id: a.action for a in result.karakter_actions},
        "mental": {a.detail_id: a.action for a in result.mental_actions},
        "softskill": {a.detail_id: a.action for a in result.softskill_actions},
    }
    
    for cat in ["karakter", "mental", "softskill"]:
        unachieved_list = state["unachieved_targets"][cat]
        
        for item in unachieved_list:
            # Ambil action dari AI jika ada, jika AI gagal / terlewat, beri fallback text
            action_text = ai_maps[cat].get(item["detail_id"], "Tingkatkan pendampingan untuk indikator ini berdasarkan laporan terbaru.")
            
            # Bentuk ulang persis seperti output dummy lama
            treatments[cat].append({
                "main_id": item["main_id"],
                "main_name": item["main_name"],
                "detail_id": item["detail_id"],
                "detail_text": item["detail_text"],
                "action": action_text
            })
    
    return {
        "insight": result.insight,
        "treatments": treatments
    }

# ==========================================
# 4. BUILD THE GRAPH
# ==========================================

workflow = StateGraph(KMSAnalysisState)

workflow.add_node("detect", detect_indicators_node)
workflow.add_node("calculate", calculate_metrics_node)
workflow.add_node("treatment", generate_insight_treatment_node)

workflow.set_entry_point("detect")
workflow.add_edge("detect", "calculate")
workflow.add_edge("calculate", "treatment")
workflow.add_edge("treatment", END)

# Inisiasi AI Graph Executor
kms_analyzer = workflow.compile()