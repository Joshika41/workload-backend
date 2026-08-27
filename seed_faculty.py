import os
import sys
import pandas as pd
import glob
import traceback
from database import SessionLocal, engine, Base, Faculty, User, RoleEnum as Role

def run_seed():
    db = SessionLocal()
    try:
        print("Resetting database...")
        db.query(User).filter(User.role == Role.FACULTY).delete(synchronize_session=False)
        db.query(Faculty).delete(synchronize_session=False)
        db.commit()
        print("Database wiped.")

        print("Scanning real section files in mca_seed_data/...")
        faculty_names = set()
        
        files = glob.glob(os.path.join("mca_seed_data", "*.xlsx"))
        print(f"Found files: {files}")
        
        if not files:
            print("CRITICAL ERROR: No .xlsx files found in mca_seed_data folder!")
            sys.exit(1)
            
        for filepath in files:
            print(f"Reading {filepath}...")
            # CRITICAL FIX: Explicitly set engine to avoid Linux auto-detect crashes
            df = pd.read_excel(filepath, engine='openpyxl')
            
            start_idx = None
            col_idx = None
            dept_col_idx = None
            
            for i in range(len(df)):
                for c in df.columns:
                    val = str(df.iloc[i][c]).strip()
                    if val == 'Name of the Faculty Member':
                        start_idx = i + 1
                        col_idx = c
                        for dc in df.columns:
                            if str(df.iloc[i][dc]).strip() == 'Dept':
                                dept_col_idx = dc
                                break
                        break
                if start_idx is not None:
                    break
                    
            if start_idx is not None and col_idx is not None and dept_col_idx is not None:
                for i in range(start_idx, len(df)):
                    dept_val = str(df.iloc[i][dept_col_idx]).strip()
                    if dept_val.upper() == 'MCA':
                        fac_str = str(df.iloc[i][col_idx]).strip()
                        if fac_str and fac_str.lower() != 'nan':
                            for name in fac_str.split('\n'):
                                clean_name = name.strip()
                                if clean_name:
                                    faculty_names.add(clean_name)
            else:
                print(f"Warning: Could not find Faculty columns in {filepath}")
                                    
        count = 0
        for name in sorted(list(faculty_names)):
            f_id = f"FAC{count+1:03d}"
            db.add(Faculty(id=f_id, name=name, department="MCA"))
            count += 1
            
        if count == 0:
            print("CRITICAL ERROR: Files were read, but 0 MCA faculty were found!")
            sys.exit(1)
                
        db.commit()
        print(f"Success: {count} real MCA Faculty members successfully extracted and loaded!")
        
    except Exception as e:
        print("--- ERROR SEEDING FACULTY ---")
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
