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
    scripts_to_run = ['seed_faculty.py', 'seed_users.py']
    
    for script in scripts_to_run:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f'Warning: {script} not found!')
            
    print('Database seeding complete!')
