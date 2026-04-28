from sqlalchemy.orm import Session
from datetime import datetime
from app.database import SessionLocal
from app.models.models import (
    Report, ReportAnalysis, ReportParameterDetection, KMSMainIndicator, KMSDetailIndicator,
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
        # 1. Jalankan Deteksi AI untuk Laporan Ini
        result = analyze_report(report.transcript)

        # 2. Simpan Analysis Meta
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

        # 3. Simpan Detections & Update Achievements (State Santri)
        detections = result.get("detections", [])
        for det in detections:
            detail_param = db.query(KMSDetailIndicator).filter(
                KMSDetailIndicator.indicator_detail.ilike(f"%{det['parameter_name']}%")
            ).first()

            if detail_param:
                db.add(ReportParameterDetection(
                    report_analysis_id=analysis.id,
                    detail_parameter_id=detail_param.id,
                    status_detected=det["status"],
                    evidence=det["evidence"]
                ))

                # Update State Achievement
                main_param = detail_param.main_indicator
                achievement = db.query(StudentAchievement).filter(
                    StudentAchievement.santri_id == report.santri_id,
                    StudentAchievement.parameter_id == main_param.id
                ).first()

                if not achievement:
                    achievement = StudentAchievement(
                        santri_id=report.santri_id,
                        parameter_id=main_param.id,
                        status=det["status"],
                        evidence_excerpt=det["evidence"]
                    )
                    db.add(achievement)
                else:
                    achievement.status = det["status"]
                    achievement.evidence_excerpt = det["evidence"]
                    achievement.last_updated = datetime.utcnow()

        db.commit()

        # 4. JALANKAN ANALISIS KUMULATIF OTOMATIS
        # Setiap laporan baru masuk, kita refresh skor dan treatment terbaru
        from app.services.analysis_service import run_analysis_for_student
        run_analysis_for_student(
            santri_id=str(report.santri_id),
            semester_id=str(report.semester_id),
            performer_id=str(report.musyrif_id),
            db=db
        )

        # 5. Update Status Laporan
        report.status = ReportStatus.analyzed
        db.commit()

    except Exception as e:
        print(f"Error saat memproses AI: {e}")
        report.status = ReportStatus.failed
        db.commit()
    finally:
        db.close()
