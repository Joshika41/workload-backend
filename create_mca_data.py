import pandas as pd
import os

os.makedirs('mca_seed_data', exist_ok=True)

# 1. Rooms
rooms_data = [
    {'venue_id': 'R1', 'venue_name': 'Room 1', 'type': 'Theory', 'capacity': 60},
    {'venue_id': 'L1', 'venue_name': 'Lab 1', 'type': 'Lab', 'capacity': 30},
]
pd.DataFrame(rooms_data).to_excel('mca_seed_data/rooms.xlsx', index=False)

# 2. Workloads
workload_data = []
for i in range(1, 20):
    workload_data.append({
        'faculty_id': f'FAC{i}',
        'faculty_name': f'Faculty {i}',
        'department': 'MCA',
        'theory_hours': 10,
        'lab_hours': 10
    })
pd.DataFrame(workload_data).to_excel('mca_seed_data/workloads.xlsx', index=False)

# 3. Requirements (8 Sections, exactly 30 hours each)
req_data = []
sections = ['MCA I-A', 'MCA I-B', 'MCA II-A', 'MCA II-B', 'MCA GEN AI I-A', 'MCA GEN AI I-B', 'MCA GEN AI II-A', 'MCA GEN AI II-B']

fac_idx = 1
for sec in sections:
    req_data.append({'section': sec, 'subject': 'Data Structures', 'subject_type': 'Theory', 'hours': 4, 'faculty_id': f'FAC{fac_idx}'})
    req_data.append({'section': sec, 'subject': 'Operating Systems', 'subject_type': 'Theory', 'hours': 4, 'faculty_id': f'FAC{fac_idx+1}'})
    req_data.append({'section': sec, 'subject': 'Database Management', 'subject_type': 'Theory', 'hours': 4, 'faculty_id': f'FAC{fac_idx+2}'})
    
    # Synchronized Elective (All sections use the same subject name so the engine links them)
    req_data.append({'section': sec, 'subject': 'Cloud Computing (Elective)', 'subject_type': 'ELECTIVE', 'hours': 4, 'faculty_id': f'FAC{fac_idx+3}'})
    
    # Labs (Require even chunks, total 30)
    req_data.append({'section': sec, 'subject': 'Python Lab', 'subject_type': 'Lab', 'hours': 4, 'faculty_id': f'FAC{fac_idx+4}'})
    req_data.append({'section': sec, 'subject': 'DBMS Lab', 'subject_type': 'Lab', 'hours': 4, 'faculty_id': f'FAC{fac_idx+5}'})
    
    # Remaining 6 hours
    req_data.append({'section': sec, 'subject': 'Software Engineering', 'subject_type': 'Theory', 'hours': 6, 'faculty_id': f'FAC{fac_idx}'})
    
    fac_idx += 1
    if fac_idx > 12:
        fac_idx = 1

pd.DataFrame(req_data).to_excel('mca_seed_data/requirements.xlsx', index=False)
print("mca_seed_data successfully mocked with 8 sections of 30 hours each!")
