import csv
import os
import sys

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine, Base
from app.models.models import KMSMainIndicator, KMSDetailIndicator

def seed_from_csv():
    print("Starting KMS seeding from CSV...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Clear existing data
        print("Clearing existing KMS indicators...")
        db.query(KMSDetailIndicator).delete()
        db.query(KMSMainIndicator).delete()
        db.commit()

        # Map to store integer ID to UUID mapping
        main_map = {}

        # --- CHARACTER ---
        print("Processing Character indicators...")
        char_main_path = 'dataset/character.csv'
        char_detail_path = 'dataset/character_micro.csv'

        if os.path.exists(char_main_path):
            with open(char_main_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    main = KMSMainIndicator(
                        category="karakter",
                        theme=row['Tema'],
                        name=row['Karakter'],
                        description=row['Penjelasan']
                    )
                    db.add(main)
                    db.flush()
                    main_map[("karakter", row['Id'])] = main.id
            print(f"  Inserted Character main indicators.")

            if os.path.exists(char_detail_path):
                with open(char_detail_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        parent_id = main_map.get(("karakter", row['id indikator global']))
                        if parent_id:
                            db.add(KMSDetailIndicator(
                                main_indicator_id=parent_id,
                                indicator_detail=row['indikator detail']
                            ))
                print(f"  Inserted Character detail indicators.")
        else:
            print(f"  Warning: {char_main_path} not found.")

        # --- MENTAL ---
        print("Processing Mental indicators...")
        mental_main_path = 'dataset/mental.csv'
        mental_detail_path = 'dataset/mental_micro.csv'

        if os.path.exists(mental_main_path):
            with open(mental_main_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    main = KMSMainIndicator(
                        category="mental",
                        theme=row['tema'],
                        name=row['mental'],
                        description=row['penjelasan']
                    )
                    db.add(main)
                    db.flush()
                    main_map[("mental", row['id'])] = main.id
            print(f"  Inserted Mental main indicators.")

            if os.path.exists(mental_detail_path):
                with open(mental_detail_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        parent_id = main_map.get(("mental", row['id_mental']))
                        if parent_id:
                            db.add(KMSDetailIndicator(
                                main_indicator_id=parent_id,
                                indicator_detail=row['indikator_detail']
                            ))
                print(f"  Inserted Mental detail indicators.")
        else:
            print(f"  Warning: {mental_main_path} not found.")

        # --- SOFTSKILL ---
        print("Processing Softskill indicators...")
        soft_main_path = 'dataset/softskill.csv'
        soft_detail_path = 'dataset/softskill_micro.csv'

        if os.path.exists(soft_main_path):
            with open(soft_main_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    main = KMSMainIndicator(
                        category="softskill",
                        theme=row['Tema'],
                        name=row['Karakter'],
                        description=row['Penjelasan']
                    )
                    db.add(main)
                    db.flush()
                    main_map[("softskill", row['Id'])] = main.id
            print(f"  Inserted Softskill main indicators.")

            if os.path.exists(soft_detail_path):
                with open(soft_detail_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        parent_id = main_map.get(("softskill", row['Id_Indikator_Global']))
                        if parent_id:
                            db.add(KMSDetailIndicator(
                                main_indicator_id=parent_id,
                                indicator_detail=row['Indikator_Detail']
                            ))
                print(f"  Inserted Softskill detail indicators.")
        else:
            print(f"  Warning: {soft_main_path} not found.")

        db.commit()
        print("\nSeeding complete!")
        
        # Summary counts
        main_count = db.query(KMSMainIndicator).count()
        detail_count = db.query(KMSDetailIndicator).count()
        print(f"Total Main Indicators: {main_count}")
        print(f"Total Detail Indicators: {detail_count}")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_from_csv()
