from database import SessionLocal, FacultyPreference

def check_db():
    db = SessionLocal()
    try:
        prefs = db.query(FacultyPreference).all()
        if not prefs:
            print("No preferences found in the database.")
            return
            
        print(f"Found {len(prefs)} preference(s):")
        print("-" * 50)
        for p in prefs:
            print(f"Faculty ID: {p.faculty_id} | Subject: {p.subject_name} | Status: {p.status}")
        print("-" * 50)
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
