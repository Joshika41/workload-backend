import os
import subprocess
import sys

def run_script(script_name):
    print(f"Running {script_name}...")
    try:
        subprocess.check_call([sys.executable, script_name])
        print(f"Successfully ran {script_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print('Starting database seeding process...')
    
    db_file = 'university_timetable.db'
    if os.path.exists(db_file):
        print('Deleting old database to ensure clean seed...')
        try:
            os.remove(db_file)
        except Exception as e:
            print(f"Warning: Could not delete database: {e}")

    # --- CRITICAL FIX: Recreate the tables so the seed scripts can use them! ---
    try:
        from database import engine, Base
        Base.metadata.create_all(bind=engine)
        print("Successfully created database tables!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)
    
    scripts_to_run = ['seed_faculty.py', 'seed_users.py']
    
    for script in scripts_to_run:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f'Warning: {script} not found!')
            
    print('Database seeding complete!')
und!')
            
    print('Database seeding complete!')
