from datetime import datetime

# sementara kita pakai logging sederhana (bisa diganti tabel notifications nanti)
def check_and_alert(student_name: str, trend: str, avg_score: float):

    if trend == "declining" or avg_score < 50:
        message = f"PERHATIAN: Performa student {student_name} menurun drastis. Segera cek laporan terbaru!"

        # sementara print/log (production nanti masuk DB / Redis / notif system)
        print({
            "timestamp": datetime.utcnow(),
            "type": "ALERT",
            "message": message
        })

        return message

    return None