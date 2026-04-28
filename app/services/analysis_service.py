"""
analysis_service.py
Shared logic untuk analisis kumulatif profiling santri.
Digunakan oleh routes/user.py dan routes/admin.py.
"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import (
    Student, Report, KMSMainIndicator, KMSDetailIndicator,
    StudentAnalysisSnapshot, SnapshotDetection, StudentAchievement, KMSProfile
)


def run_analysis_for_student(
    santri_id: str,
    semester_id: str,
    performer_id: Optional[str],
    db: Session
) -> dict:
    """
    Jalankan analisis kumulatif untuk satu santri dalam satu semester.
    Mengembalikan dict hasil snapshot yang baru dibuat.
    """

    # ── 1. Cari snapshot terakhir (sebagai baseline) ──────────────────────────
    prev_snapshot = (
        db.query(StudentAnalysisSnapshot)
        .filter(
            StudentAnalysisSnapshot.santri_id == santri_id,
            StudentAnalysisSnapshot.semester_id == semester_id
        )
        .order_by(StudentAnalysisSnapshot.performed_at.desc())
        .first()
    )

    # Kumpulkan detail_indicator_id yang sudah terdeteksi sebelumnya
    prev_detected_detail_ids: set = set()
    if prev_snapshot:
        for det in prev_snapshot.detected_indicators:
            prev_detected_detail_ids.add(str(det.detail_indicator_id))

    # ── 2. Ambil laporan baru yang belum dianalisis ───────────────────────────
    report_query = db.query(Report).filter(
        Report.santri_id == santri_id,
        Report.semester_id == semester_id
    )
    if prev_snapshot and prev_snapshot.analyzed_up_to:
        report_query = report_query.filter(
            Report.created_at > prev_snapshot.analyzed_up_to
        )

    new_reports = report_query.order_by(Report.created_at.asc()).all()

    if not new_reports and not prev_snapshot:
        return {"error": "Belum ada laporan untuk santri ini di semester terpilih."}

    # Gabungkan transcript laporan baru
    combined_transcript = " ".join(
        r.transcript.lower() for r in new_reports if r.transcript
    ).strip()

    newest_report_time = (
        max(r.created_at for r in new_reports) if new_reports else
        (prev_snapshot.analyzed_up_to if prev_snapshot else datetime.utcnow())
    )

    # ── 3. Ambil semua indikator ──────────────────────────────────────────────
    all_mains = db.query(KMSMainIndicator).all()
    all_details = db.query(KMSDetailIndicator).all()

    # ── 4. Deteksi indikator BARU dari transcript laporan baru ────────────────
    newly_detected: list[tuple[KMSDetailIndicator, str]] = []  # (detail, evidence)
    for det in all_details:
        if str(det.id) in prev_detected_detail_ids:
            continue  # sudah terdeteksi sebelumnya, lewati
        keyword = det.indicator_detail.lower().strip()
        if keyword and keyword in combined_transcript:
            # Ambil potongan konteks sebagai evidence
            idx = combined_transcript.find(keyword)
            start = max(0, idx - 40)
            end = min(len(combined_transcript), idx + len(keyword) + 40)
            evidence = "..." + combined_transcript[start:end].strip() + "..."
            newly_detected.append((det, evidence))

    # ── 5. Gabungkan semua deteksi (lama + baru) ─────────────────────────────
    all_detected_detail_ids: set = prev_detected_detail_ids | {
        str(d.id) for d, _ in newly_detected
    }

    # ── 6. Tentukan indikator UTAMA yang tercapai ─────────────────────────────
    # Rule: cukup 1 detail terdeteksi → main indicator dianggap tercapai
    achieved_main_ids: set = set()
    for main in all_mains:
        for detail in main.details:
            if str(detail.id) in all_detected_detail_ids:
                achieved_main_ids.add(str(main.id))
                break

    # ── 7. Hitung skor K/M/S ─────────────────────────────────────────────────
    cat_data: dict = {}
    for cat in ["karakter", "mental", "softskill"]:
        mains_in_cat = [m for m in all_mains if m.category == cat]
        total = len(mains_in_cat) or 1
        achieved = len([m for m in mains_in_cat if str(m.id) in achieved_main_ids])
        score = round((achieved / total) * 100, 1)
        cat_data[cat] = {
            "total": total,
            "achieved": achieved,
            "score": score,
            "mains": mains_in_cat
        }

    overall_score = round(
        (cat_data["karakter"]["score"] + cat_data["mental"]["score"] + cat_data["softskill"]["score"]) / 3, 1
    )

    # ── 8. Kumpulkan indikator belum tercapai per kategori ────────────────────
    def get_unachieved(cat: str) -> list:
        """
        Ambil maks 3 indikator yang belum tercapai per kategori.
        Hasilnya adalah data indikator TANPA action — action akan di-generate AI.
        """
        result = []
        for main in cat_data[cat]["mains"]:
            if str(main.id) in achieved_main_ids:
                continue  # sudah tercapai, skip
            for detail in main.details:
                if str(detail.id) not in all_detected_detail_ids:
                    result.append({
                        "main_id": str(main.id),
                        "main_name": main.name,
                        "detail_id": str(detail.id),
                        "detail_text": detail.indicator_detail,
                    })
                    break  # 1 detail representative per main
            if len(result) >= 3:
                break
        return result

    unachieved_k = get_unachieved("karakter")
    unachieved_m = get_unachieved("mental")
    unachieved_s = get_unachieved("softskill")

    # ── 9. Panggil AI — generate treatment yang dipersonalisasi ───────────────
    # AI menerima transcript santri + indikator yang belum tercapai,
    # lalu generate kalimat tindakan yang disesuaikan kondisi santri.
    from app.core.ai_engine import generate_treatment

    ai_actions = generate_treatment(
        transcript=combined_transcript,
        unachieved_per_cat={
            "karakter": unachieved_k,
            "mental": unachieved_m,
            "softskill": unachieved_s,
        }
    )

    # Gabungkan data indikator + action AI → list treatment per kategori
    def merge_with_action(items: list, actions: list) -> list:
        return [
            {**item, "action": actions[i] if i < len(actions) else ""}
            for i, item in enumerate(items)
        ]

    treatment_k = merge_with_action(unachieved_k, ai_actions.get("karakter", []))
    treatment_m = merge_with_action(unachieved_m, ai_actions.get("mental", []))
    treatment_s = merge_with_action(unachieved_s, ai_actions.get("softskill", []))

    # ── 9. Generate Insight ───────────────────────────────────────────────────
    total_achieved = len(achieved_main_ids)
    total_all = len(all_mains)
    insight = (
        f"Analisis kumulatif dari {len(new_reports)} laporan terbaru "
        f"(total kumulatif: {len(new_reports) + (prev_snapshot.reports_included if prev_snapshot else 0)} laporan). "
        f"{total_achieved} dari {total_all} indikator utama telah tercapai. "
        f"Karakter: {cat_data['karakter']['score']}% "
        f"({cat_data['karakter']['achieved']}/{cat_data['karakter']['total']}), "
        f"Mental: {cat_data['mental']['score']}% "
        f"({cat_data['mental']['achieved']}/{cat_data['mental']['total']}), "
        f"Softskill: {cat_data['softskill']['score']}% "
        f"({cat_data['softskill']['achieved']}/{cat_data['softskill']['total']})."
    )

    # ── 10. Simpan Snapshot ───────────────────────────────────────────────────
    snapshot = StudentAnalysisSnapshot(
        santri_id=santri_id,
        semester_id=semester_id,
        performed_by=performer_id,
        performed_at=datetime.utcnow(),
        reports_included=len(new_reports),
        analyzed_up_to=newest_report_time,
        karakter_score=cat_data["karakter"]["score"],
        mental_score=cat_data["mental"]["score"],
        softskill_score=cat_data["softskill"]["score"],
        overall_score=overall_score,
        karakter_achieved=cat_data["karakter"]["achieved"],
        karakter_total=cat_data["karakter"]["total"],
        mental_achieved=cat_data["mental"]["achieved"],
        mental_total=cat_data["mental"]["total"],
        softskill_achieved=cat_data["softskill"]["achieved"],
        softskill_total=cat_data["softskill"]["total"],
        insight=insight,
        treatment_k=json.dumps(treatment_k, ensure_ascii=False),
        treatment_m=json.dumps(treatment_m, ensure_ascii=False),
        treatment_s=json.dumps(treatment_s, ensure_ascii=False),
    )
    db.add(snapshot)
    db.flush()  # dapatkan snapshot.id sebelum commit

    # Simpan deteksi BARU saja ke SnapshotDetection
    for det, evidence in newly_detected:
        db.add(SnapshotDetection(
            snapshot_id=snapshot.id,
            main_indicator_id=det.main_indicator_id,
            detail_indicator_id=det.id,
            evidence_excerpt=evidence
        ))

    # Update StudentAchievement (current state, untuk backward compat)
    for main in all_mains:
        status = "gained" if str(main.id) in achieved_main_ids else "undefined"
        ach = db.query(StudentAchievement).filter(
            StudentAchievement.santri_id == santri_id,
            StudentAchievement.parameter_id == main.id
        ).first()
        if not ach:
            ach = StudentAchievement(
                santri_id=santri_id,
                parameter_id=main.id,
                status=status
            )
            db.add(ach)
        else:
            ach.status = status
            ach.last_updated = datetime.utcnow()

    # Update KMSProfile (current score)
    profile = db.query(KMSProfile).filter(
        KMSProfile.santri_id == santri_id,
        KMSProfile.semester_id == semester_id
    ).first()
    if not profile:
        profile = KMSProfile(santri_id=santri_id, semester_id=semester_id)
        db.add(profile)

    profile.karakter_score = cat_data["karakter"]["score"]
    profile.mental_score = cat_data["mental"]["score"]
    profile.softskill_score = cat_data["softskill"]["score"]
    profile.overall_score = overall_score
    profile.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(snapshot)

    # ── 11. Bangun Response ───────────────────────────────────────────────────
    return _build_snapshot_response(snapshot, all_detected_detail_ids, newly_detected, cat_data)


def _build_snapshot_response(
    snapshot: StudentAnalysisSnapshot,
    all_detected_detail_ids: set,
    newly_detected: list,
    cat_data: dict
) -> dict:
    """Format response snapshot analisis."""
    return {
        "snapshot_id": str(snapshot.id),
        "performed_at": snapshot.performed_at.isoformat(),
        "reports_included": snapshot.reports_included,
        "newly_detected_count": len(newly_detected),
        "scores": {
            "karakter": {
                "score": snapshot.karakter_score,
                "achieved": snapshot.karakter_achieved,
                "total": snapshot.karakter_total
            },
            "mental": {
                "score": snapshot.mental_score,
                "achieved": snapshot.mental_achieved,
                "total": snapshot.mental_total
            },
            "softskill": {
                "score": snapshot.softskill_score,
                "achieved": snapshot.softskill_achieved,
                "total": snapshot.softskill_total
            },
            "overall": snapshot.overall_score
        },
        "insight": snapshot.insight,
        "treatment": {
            "karakter": json.loads(snapshot.treatment_k or "[]"),
            "mental": json.loads(snapshot.treatment_m or "[]"),
            "softskill": json.loads(snapshot.treatment_s or "[]")
        },
        "newly_detected_indicators": [
            {
                "main_id": str(d.main_indicator_id),
                "detail_id": str(d.id),
                "detail_text": d.indicator_detail,
                "evidence": ev
            }
            for d, ev in newly_detected
        ]
    }


def format_full_snapshot(snapshot: StudentAnalysisSnapshot) -> dict:
    """Format snapshot untuk endpoint history analisis."""
    all_detections = []
    for det in snapshot.detected_indicators:
        all_detections.append({
            "main_id": str(det.main_indicator_id),
            "main_name": det.main_indicator.name if det.main_indicator else None,
            "main_category": det.main_indicator.category if det.main_indicator else None,
            "detail_id": str(det.detail_indicator_id),
            "detail_text": det.detail_indicator.indicator_detail if det.detail_indicator else None,
            "evidence": det.evidence_excerpt
        })

    return {
        "snapshot_id": str(snapshot.id),
        "performed_at": snapshot.performed_at.isoformat(),
        "performed_by": str(snapshot.performed_by) if snapshot.performed_by else None,
        "reports_included": snapshot.reports_included,
        "analyzed_up_to": snapshot.analyzed_up_to.isoformat() if snapshot.analyzed_up_to else None,
        "scores": {
            "karakter": {
                "score": snapshot.karakter_score,
                "achieved": snapshot.karakter_achieved,
                "total": snapshot.karakter_total
            },
            "mental": {
                "score": snapshot.mental_score,
                "achieved": snapshot.mental_achieved,
                "total": snapshot.mental_total
            },
            "softskill": {
                "score": snapshot.softskill_score,
                "achieved": snapshot.softskill_achieved,
                "total": snapshot.softskill_total
            },
            "overall": snapshot.overall_score
        },
        "insight": snapshot.insight,
        "treatment": {
            "karakter": json.loads(snapshot.treatment_k or "[]"),
            "mental": json.loads(snapshot.treatment_m or "[]"),
            "softskill": json.loads(snapshot.treatment_s or "[]")
        },
        "detected_indicators": all_detections
    }
