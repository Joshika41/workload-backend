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
    
    # Delete the corrupted database so Render builds a fresh one from Excel files
    db_file = 'university_timetable.db'
    if os.path.exists(db_file):
        print('Deleting old database to ensure clean seed...')
        try:
            os.remove(db_file)
        except Exception as e:
            print(f"Warning: Could not delete database: {e}")

    scripts_to_run = ['seed_faculty.py', 'seed_users.py']
    
    for script in scripts_to_run:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f'Warning: {script} not found!')
            
    print('Database seeding complete!')
