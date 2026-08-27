import os
import sys
from sqlalchemy.orm import Session
from database import SessionLocal, Faculty, User, RoleEnum as Role
from auth import get_password_hash

def generate_username(name):
    # E.g. "Dr. R. Anandan" -> "ranandan"
    clean = name.replace('Dr. ', '').replace('Prof. ', '').replace('Mr. ', '').replace('Ms. ', '').strip()
    parts = clean.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1]).lower().replace('.', '')
    return clean.lower().replace('.', '').replace(' ', '')

def run_seed():
    db = SessionLocal()
    try:
        print("Generating credentials for real faculty...")
        
        # Read real faculty from DB
        faculties = db.query(Faculty).all()
        
        print("\n--- GENERATED CREDENTIALS ---")
        print(f"{'Name':<25} | {'Username':<15} | {'Password':<15}")
        print("-" * 60)
        
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
            
            # Check if user exists
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                db.add(User(
                    username=username,
                    password_hash=get_password_hash("password123"),
                    role=Role.FACULTY,
                    faculty_id=fac.id
                ))
                count += 1
                print(f"{fac.name:<25} | {username:<15} | {'password123':<15}")
            else:
                print(f"{fac.name:<25} | {username:<15} | (Already Exists)")
                
        db.commit()
        print("-" * 60)
        print(f"Success: {count} User accounts successfully generated!")
        
    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
