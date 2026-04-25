import uuid
from app.database import SessionLocal, engine, Base
from app.models.models import KMSParameter

def seed_parameters():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Data Karakter (40)
    karakter_data = [
        ("Tujuan Penciptaan Manusia", "Memiliki tujuan hidup", "Allah Swt tidak menciptakan manusia hanya untuk main-main..."),
        ("Tujuan Penciptaan Manusia", "Mampu memimpin & dipimpin", "Tujuan penciptaan yang pertama adalah menjadi pemimpin (khalifah)..."),
        ("Tujuan Penciptaan Manusia", "Mampu mengatur diri & waktu dengan baik.", "Tujuan penciptaan yang Allah canangkan tidak mungkin akan dapat dicapai..."),
        ("Tujuan Penciptaan Manusia", "Terlibat dalam kehidupan sosial & suka membantu", "Tujuan penciptaan manusia adalah ; agar manusia menjadi pemimpin..."),
        ("Tujuan Penciptaan Manusia", "Konsisten ibadahnya & memiliki hubungan yang kuat dengan Al-Quran", "Apabila manusia tidak beribadah, maka jelas 1 tujuan penciptaan gagal ia raih..."),
        ("Alat Belajar Manusia", "Rasa ingin tahunya besar & gemar membaca", "'Belajar' adalah perintah pertama yang turun melalui ayat QS Al-Alaq..."),
        ("Alat Belajar Manusia", "Berpikir terbuka & suka mencoba hal baru.", "Manusia yang menjalankan perintah Allah yang pertama..."),
        ("Alat Belajar Manusia", "Imajinasinya kaya (Sumber K2IAM)", "Awalnya semua manusia pandai menghayal, semestinya ini adalah pondasi..."),
        ("Alat Belajar Manusia", "Berjuang memfilter 3 alat belajar.", "Manusia yang banyak membaca, ia akan kaya dengan pengetahuan..."),
        ("Sumber kejahatan", "Menjadikan Islam sebagai identitas diri yang utama.", "Sumber kejahatan manusia adalah hawa nafsu dan syaithan..."),
        ("Sumber kejahatan", "Menjadikan Islam sebagai sumber kebenaran.", "Agama Islam adalah patokan atau rujukan dari semua nilai..."),
        ("Sumber kejahatan", "Menjadikan Islam sebagai panduan dalam berpikir, berkata, & bertindak.", "Seorang mukmin yang taat dan patuh kepada Islam tentu akan menjadikan Al-Quran..."),
        ("Sumber kejahatan", "Berusaha keras untuk berbuat benar.", "'Manusia memang bukan malaikat yang pasti berbuat benar...'"),
        ("Sumber kejahatan", "Berusaha keras mencegah dirinya berbuat salah.", "Manusia memang bukan malaikat yang pasti berbuat benar..."),
        ("Sumber kejahatan", "Memilih lingkungan & teman agar agama nya terjaga.", "Salah satu cara agar manusia selalu ingin berbuat benar..."),
        ("Akhirat prioritas", "Menyadari bahwa dunia itu penting hanya karena itulah sat-satunya jalan menuju akhirat.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham bahwa manusia sedang melakukan perjalanan..."),
        ("Akhirat prioritas", "Cita-cita, visi, dan misinya dunia sekaligus akhirat.", "Berdasarkan pemahaman tentang kesementaraan dunia..."),
        ("Akhirat prioritas", "Menjadikan Allah, Quran dan Nabi Saw sebagai prioritas yang lebih besar dari semua urusan.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham..."),
        ("Makna ujian", "Memahami bahwa ujian adalah keniscayaan.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham bahwa manusia di dunia ini hakikatnya adalah sedang menjalani ujian..."),
        ("Makna ujian", "Memahami bahwa bentuk ujian itu berupa tawa & tangis.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham bahwa manusia di dunia ini hakikatnya adalah sedang menjalani ujian..."),
        ("Makna ujian", "Memahami bahwa ujian berupa tangis harus dijawab dengan jihad dan sabar (terus berikhtiar).", "Mukmin yang mempelajari Al-Quran akan tahu dan paham bahwa manusia di dunia ini hakikatnya adalah sedang menjalani ujian..."),
        ("Makna ujian", "Memahami bahwa ujian berupa tawa harus dijawab dengan kendali diri, jangan sombong dan bermaksiat.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham bahwa manusia di dunia ini hakikatnya adalah sedang menjalani ujian..."),
        ("Makna ujian", "Memahami bahwa ujian itu adalah peluang untuk berkembang.", "Apabila manusia jeli, maka akan jelaslah bahwa disetiap ujian terkandung peluang..."),
        ("Makna ujian", "Memiliki daya tahan yang baik terhadap tekanan, kesulitan, & stress.", "Semua ujian menuntut fokus dan energi tambahan..."),
        ("Makna ujian", "Mampu menemukan hikmah dibalik ujian (baik di awal, di tengah, maupun di akhir)", "Apabila manusia jeli, maka akan jelaslah bahwa disetiap ujian terkandung hikmah..."),
        ("Makna jihad", "Setia dengan tujuan & yakin bahwa tujuan itu akan tercapai.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham bahwa manusia di dunia ini hakikatnya adalah sedang menjalani perjalanan..."),
        ("Makna jihad", "Memiliki endurance (kekuatan menderita) yang baik.", "Mukmin yang jeli akan mendapati sebuah kenyataan..."),
        ("Makna jihad", "Lebih terobsesi pada proses (ikhtiar) daripada hasil.", "Disetiap ujian ada yang namanya 'hasil' dan ada yang namanya 'proses'..."),
        ("Makna jihad", "Menerima kegagalan dengan baik & pandai mengambil hikmah untuk ikhtiar berikutnya.", "Disetiap ujian ada yang namanya berhasil ada yang namanya gagal..."),
        ("Makna taqdir", "Menerima masa lalu sebagai taqdir Allah yang terbaik.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham tentang konsep takdir..."),
        ("Makna taqdir", "Mengartikan masa depan sebagai tanggung jawab pribadi.", "Mukmin yang baik dilarang menyalahkan masa lalu..."),
        ("Makna taqdir", "Memahami bahwa manusia diberi hak untuk memilih & semua pilihan itu adalah taqdir Allah.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham tentang konsep takdir..."),
        ("Makna taqdir", "Pandai menetapkan pilihan dengan argumentasi logis yang syar’i.", "Mukmin yang mempelajari Al-Quran akan tahu dan paham bahwa Allah memberikan hak pilih kepada manusia..."),
        ("Makna taqdir", "Memahami bahwa setiap pilihan ada resiko & konsekuensinya.", "Mukmin yang cerdas juga paham bahwa Allah memberikan banyak pilihan..."),
        ("Makna taqdir", "Menerima kesalahan dengan wajar & tidak menyalahkan apapun dan siapapun tanpa argumentasi yang logis dan syar’i", "Mukmin yang dewasa dan cerdas akan mengambil semua tanggung jawab..."),
        ("Makna ukhuwah", "Memahami konflik sebagai ujian & alat untuk belajar.", "Arti sejati dari ukhuwah adalah ikatan persaudaraan..."),
        ("Makna ukhuwah", "Memahami makna dari kata benar, baik, & indah.", "Ada tiga nilai yang harus dipahami dengan sempurna..."),
        ("Makna ukhuwah", "Menyikapi konflik dengan ; “Tabayun. Muhasabah, & Ishlah", "Tabayun adalah memastikan kebenaran informasi..."),
        ("Makna ukhuwah", "Memahami bahwa perbedaan adalah kehendak Allah & akibat dari perspektif yang berbeda.", "Apa arti konflik ? konflik adalah pertentangan..."),
        ("Makna ukhuwah", "Pandai menyikapi perbedaan dengan indah (benar & baik).", "Ini sudah dibahas dengan sangat jelas di ayat-ayat pondasi...")
    ]

    # Data Mental (34)
    mental_data = [
        ("Niat", "Prinsip belajar", "Belajar itu adalah ibadah. Belajar itu untuk tahu dan bisa..."),
        ("Niat", "Tahu prioritas dari Indah, Benar, dan baik.", "Prioritas 1 adalah indah yaitu gabungan dari benar dan baik..."),
        ("Niat", "Sumpah SI 1 “Bahagia menjadi hamba Allah & siap menghadapNya.”", "Ada dua kata penting disini, 'Hamba' dan 'bahagia'..."),
        ("Niat", "Sumpah SI 2 “Bahagia menjadi umat Muhammad Saw & merindukan perjumpaan dengannya.”", "Mencintai orang yang tak pernah kita lihat, itu masalah besar..."),
        ("Niat", "Sumpah SI 3 “Jatuh cinta pada kalam Allah & siap hidup berpandu padanya.”", "Al-Quran adalah kalam Allah, Al-Quran adalah jejak Allah paling nyata..."),
        ("Niat", "Sumpah SI 4 “Ingin mulia di akhirat dengan menghafal alQuran.”", "Mukmin yang hebat, bukan cuma pembaca saja..."),
        ("Niat", "Sumpah SI 4 “Ingin Mulia di dunia dengan teknologi bisnis & dakwah.”", "Mukmin yang hebat tidak gagap dengan kehidupan dunia..."),
        ("Niat", "Berpikir Besar", "Apa yang kamu inginkan itulah yang kamu dapat, Berpikirlah yang besar..."),
        ("Niat", "Tidak ada rasa malu kecuali", "Ketika terpikir mau berbuat dosa. Ketika sedang berbuat dosa. dan Setelah melakukan dosa..."),
        ("Niat", "Mental Inisiatif", "Adalah kemampuan untuk bertindak tanpa menunggu perintah..."),
        ("Niat", "Kreatif / Daya cipta", "Adalah kemampuan mencipta sesuatu. Kemampuan untuk mencari ide..."),
        ("Niat", "Inovatif / Daya rubah", "Adalah kemampuan memodifikasi sesuatu. Kemampuan untuk memodifikasi..."),
        ("Niat", "Mandiri", "Kemampuan untuk hidup dengan matang, baik : Secara emosional, Perilaku, dan Nilai..."),
        ("Niat", "Punya action plan", "Punya rencana kehidupan yang ditulis secara rinci..."),
        ("Jihad", "Sumpah SI 6 “Sadar bahwa dunia adalah game yang besar.”", "Seorang mukmin yang jeli, ia akan melihat bahwa dunia ini mirip game..."),
        ("Jihad", "Sumpah SI 7 “Setiap pilihan ada konsekuensinya.”", "Hidup ini dipenuhi pilihan. Kita harus memilih..."),
        ("Jihad", "Daya juang", "Daya juang adalah : Kemampuan untuk terus berikhtiar..."),
        ("Jihad", "Kompetitif (Daya saing)", "Adalah kemampuan untuk : Bersaing, Merespon dengan benar kemenangan..."),
        ("Jihad", "Monetitatif (Daya menguangkan)", "Kemampuan untuk menghasilkan uang dari suatu produk..."),
        ("Jihad", "Cara belajar", "Belajar merupakan aktivitas yang paling penting..."),
        ("Jihad", "Mulai dari enol", "Semua orang sukses : selalu mulai dari enol, tidak ada yang instant..."),
        ("Jihad", "Mental belajar", "Mental belajar adalah semangat untuk terus belajar..."),
        ("Jihad", "Kontrol potensi", "Manusia sukses adalah mereka : yang tahu potensi dirinya..."),
        ("Jihad", "Tiga kekuatan internal", "Manusia sukses adalah mereka yang memiliki tiga kekuatan..."),
        ("Sabar", "Sumpah SI 8 “Semua baik dan menjadi alat belajar.”", "Mukmin sejati tak pernah menyalahkan orang lain atau keadaan..."),
        ("Sabar", "Sumpah SI 9 “Aku bagian dari masyarakat.”", "Salah satu tujuan penciptaan adalah menjadi manusia yang bermanfaat..."),
        ("Sabar", "Sumpah SI 10 “Aku sedang menulis kitabku sendiri.”", "Allah yang maha perkasa saja menciptakan lauhil mahfudz untuk mencatat..."),
        ("Sabar", "Empat suara di dalam diri", "Suara malaikat, Suara syaithan, Suara kita yang pro dengan malaikat..."),
        ("Sabar", "Kontrol Diri", "Manusia yang sukses adalah mereka yang memiliki kemampuan untuk mengendalikan diri..."),
        ("Sabar", "Mental Antisipatif (Daya tangkal)", "Antispasi adalah daya menangkal masalah..."),
        ("Sabar", "Keseimbangan 4 waktu", "Untuk mempertahankan prestasi kita harus menyeimbangkan 4 waktu..."),
        ("Sabar", "Mental ITMI", "Mental ITMI adalah kemampuan untuk menepis mudorotnya teknologi..."),
        ("Sabar", "Mental menghargai karya sendiri", "Kemampuan menghargai karya sendiri, mensyukuri pencapaian..."),
        ("Sabar", "Konflik manajemen", "Mental yang baik dalam mencegah dan menangani konflik adalah...")
    ]

    # Data Soft Skill (14)
    softskill_data = [
        ("Kharisma", "Keinginan untuk selalu mengembangkan diri.", "Kharisma ini adalah karunia Allah Swt..."),
        ("Kharisma", "Kesetiaan pada Agama dalam wujud berbuat benar", "'Kesetiaan pada agama' adalah pondasi yang vital..."),
        ("Kharisma", "Menyayangi manusia dalam wujud memaafkan & memaklumi.", "Hampir semua konflik dipicu oleh respon yang buruk..."),
        ("Power", "Kesetiaan pada tujuan.", "Power ini adalah karunia Allah Swt. Power adalah kekuatan seseorang..."),
        ("Power", "Kemauan untuk berkurban demi tercapainya tujuan.", "Kesetiaan pada tujuan, tidak mungkin tegak tanpa kesiapan..."),
        ("Power", "Kekuatan untuk mengelola konflik.", "Konflik adalah bagian tak terpisahkan dari perjalanan..."),
        ("Power", "Keberanian untuk mengambil keputusan dan menanggung resikonya.", "Seperti semua perjalanan menuju suatu tujuan..."),
        ("Authority", "Memahami what ia buat atau rencanakan (masterplan).", "Authority ini adalah kualitas yang akan tumbuh..."),
        ("Authority", "Pandai membujuk orang (Persuasif).", "Authority atau Wewenang bukan hanya soal memberi instruksi..."),
        ("Authority", "Pandai memaksa orang (Imperatif).", "Terkadang kita berhadapan dengan orang yang tidak ingin..."),
        ("Influential", "Kemampuan komunikasi dalam wujud interaksi & negoisasi.", "Influential adalah kualitas yang akan muncul..."),
        ("Influential", "Kepandaian memilih diksi yang mumpuni.", "Komunikasi mestinya bukan sekedar kata-kata biasa..."),
        ("Influential", "Daya ajak yang kuat.", "Kata-kata indah yang tidak dibarengi dengan daya ajak yang kuat..."),
        ("Influential", "Tauladan yang selaras dengan pikiran dan kata-katanya.", "Kata-kata yang indah akan kehilangan makna jika tidak sejalan...")
    ]

    for theme, name, desc in karakter_data:
        p = KMSParameter(category="karakter", theme=theme, name=name, description=desc)
        db.add(p)
    
    for theme, name, desc in mental_data:
        p = KMSParameter(category="mental", theme=theme, name=name, description=desc)
        db.add(p)
        
    for theme, name, desc in softskill_data:
        p = KMSParameter(category="softskill", theme=theme, name=name, description=desc)
        db.add(p)

    db.commit()
    print("Seeding KMS Parameters complete!")
    db.close()

if __name__ == "__main__":
    seed_parameters()
