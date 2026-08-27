import pandas as pd
import os

target_dir = 'mca_seed_data'
os.makedirs(target_dir, exist_ok=True)

data = {
    'Venue ID': [
        '103', '104', '301', '302', '303', '304', '305', '306', # Actual Classrooms
        'Lab 1', 'Lab 2'                                        # The ONLY two labs
    ],
    'Venue Name': [
        'Classroom 103', 'Classroom 104', 'Classroom 301', 'Classroom 302', 
        'Classroom 303', 'Classroom 304', 'Classroom 305', 'Classroom 306',
        'Computer Lab 1', 'Computer Lab 2'
    ],
    'Type': [
        'Theory', 'Theory', 'Theory', 'Theory', 'Theory', 'Theory', 'Theory', 'Theory', 
        'Lab', 'Lab'
    ],
    'Capacity': [70, 70, 70, 70, 70, 70, 70, 70, 60, 60]
}

df_rooms = pd.DataFrame(data)
file_path = os.path.join(target_dir, 'Room_Lab_List.xlsx')
df_rooms.to_excel(file_path, index=False)

print(f"Success: Real-world University Matrix saved to {file_path}!")