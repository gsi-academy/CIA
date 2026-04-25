from sqlalchemy.orm import Session
from datetime import datetime
from app.database import SessionLocal
from app.models.models import (
    Report, ReportAnalysis, ReportParameterDetection, KMSParameter,
    StudentAchievement, KMSProfile, Treatment, ReportStatus
)
from app.core.ai_engine import analyze_report

def process_ai(report_id: str):
    db = SessionLocal()
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        db.close()
        return

    try:
        # 1. Jalankan AI
        result = analyze_report(report.transcript)

        # 2. Simpan Analysis
        analysis = ReportAnalysis(
            report_id=report.id,
            insight=result.get("insight"),
            recommendation=result.get("recommendation"),
            raw_llm_output=str(result),
            model_used="gpt-4o-mini",
            processing_ms=0
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # 3. Simpan Detections & Update Achievements
        detections = result.get("detections", [])
        for det in detections:
            # Cari parameter di master
            param = db.query(KMSParameter).filter(
                (KMSParameter.name.ilike(f"%{det['parameter_name']}%")) |
                (KMSParameter.description.ilike(f"%{det['parameter_name']}%"))
            ).first()

            if param:
                # Simpan History Deteksi
                db.add(ReportParameterDetection(
                    report_analysis_id=analysis.id,
                    parameter_id=param.id,
                    status_detected=det["status"],
                    evidence=det["evidence"]
                ))

                # Update State Achievement Santri
                achievement = db.query(StudentAchievement).filter(
                    StudentAchievement.santri_id == report.santri_id,
                    StudentAchievement.parameter_id == param.id
                ).first()

                if not achievement:
                    achievement = StudentAchievement(
                        santri_id=report.santri_id,
                        parameter_id=param.id,
                        status=det["status"],
                        evidence_excerpt=det["evidence"]
                    )
                    db.add(achievement)
                else:
                    # Update jika status berubah atau baru terdeteksi
                    achievement.status = det["status"]
                    achievement.evidence_excerpt = det["evidence"]
                    achievement.last_updated = datetime.utcnow()

        db.commit()

        # 4. HITUNG ULANG SKOR (KMS PROFILE)
        gained_counts = {
            "karakter": db.query(StudentAchievement).join(KMSParameter).filter(
                StudentAchievement.santri_id == report.santri_id,
                KMSParameter.category == "karakter",
                StudentAchievement.status == "gained"
            ).count(),
            "mental": db.query(StudentAchievement).join(KMSParameter).filter(
                StudentAchievement.santri_id == report.santri_id,
                KMSParameter.category == "mental",
                StudentAchievement.status == "gained"
            ).count(),
            "softskill": db.query(StudentAchievement).join(KMSParameter).filter(
                StudentAchievement.santri_id == report.santri_id,
                KMSParameter.category == "softskill",
                StudentAchievement.status == "gained"
            ).count()
        }

        profile = db.query(KMSProfile).filter(
            KMSProfile.santri_id == report.santri_id,
            KMSProfile.semester_id == report.semester_id
        ).first()

        if not profile:
            profile = KMSProfile(
                santri_id=report.santri_id,
                semester_id=report.semester_id
            )
            db.add(profile)

        profile.karakter_score = (gained_counts["karakter"] / 40) * 100
        profile.mental_score = (gained_counts["mental"] / 34) * 100
        profile.softskill_score = (gained_counts["softskill"] / 14) * 100
        profile.overall_score = (profile.karakter_score + profile.mental_score + profile.softskill_score) / 3
        profile.report_count += 1
        profile.last_updated = datetime.utcnow()

        # 5. SIMPAN TREATMENT
        db.add(Treatment(
            santri_id=report.santri_id,
            semester_id=report.semester_id,
            generated_from_report=report.id,
            recommendation=result.get("recommendation", "Pantau terus perkembangan santri."),
            priority="medium",
            status="pending"
        ))

        # 6. Update Status Laporan
        report.status = ReportStatus.analyzed
        db.commit()

    except Exception as e:
        print(f"Error saat memproses AI: {e}")
        report.status = ReportStatus.failed
        db.commit()
    finally:
        db.close()
