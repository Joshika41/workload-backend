import os
import sys
from sqlalchemy.orm import Session
from database import SessionLocal, Faculty, User, RoleEnum as Role

def generate_username(name):
    clean = name.replace('Dr. ', '').replace('Prof. ', '').replace('Mr. ', '').replace('Ms. ', '').strip()
    parts = clean.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1]).lower().replace('.', '')
    return clean.lower().replace('.', '').replace(' ', '')

def run_seed():
    db = SessionLocal()
    try:
        print("Generating credentials for real faculty...")
        faculties = db.query(Faculty).all()
        
        # This is the exact pre-calculated security hash for "password123"
        # Using this directly completely bypasses the cloud library bug!
        hardcoded_hash = "$2b$12$uxFrTo/ZvbrnfxCuLim0guX4pBy7rfez6dhKFWFikOGaz1ZIs.QMO"
        
        count = 0
        seen_usernames = set()
        for fac in faculties:
            base_username = generate_username(fac.name)
            username = base_username
            suffix = 1
            while username in seen_usernames:
                username = f"{base_username}{suffix}"
                suffix += 1
            seen_usernames.add(username)
            
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                db.add(User(
                    username=username,
                    password_hash=hardcoded_hash,
                    role=Role.FACULTY,
                    faculty_id=fac.id
                ))
                count += 1
                
        # --- Create Admin and Dean Users ---
        print("\nSeeding admin and dean users...")
        for default_user in [("admin", Role.ADMIN), ("dean", Role.DEAN)]:
            username, role = default_user
            if not db.query(User).filter(User.username == username).first():
                db.add(User(username=username, password_hash=hardcoded_hash, role=role))
                print(f"Created {username} user")

        db.commit()
        print(f"Success: {count} Faculty accounts and Admin/Dean successfully generated!")
        
    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
