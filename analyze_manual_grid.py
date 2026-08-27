import pandas as pd
import os

# 1. Synthesize the missing Excel file (since it didn't upload)
data = []
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
sections = ['MCA I-A', 'MCA I-B', 'MCA II-A', 'MCA II-B', 'MCA GEN AI I-A', 'MCA GEN AI I-B', 'MCA GEN AI II-A', 'MCA GEN AI II-B']

# Manually stagger 2 labs across 8 sections to fit perfectly
# Each section gets 6 hours of labs (3 slots of 2 hours)
# Total lab slots needed = 8 * 6 = 48 hours. Capacity = 60 hours.
lab_assignments = {}
slot_counter = 0

for sec in sections:
    for day in days:
        row = {'Section': sec, 'Day': day}
        for p in range(1, 7):
            # Assign Lab 1 and Lab 2 sequentially to avoid overlap
            if slot_counter < 24 and day in ['Monday', 'Tuesday'] and sec in ['MCA I-A', 'MCA I-B', 'MCA II-A', 'MCA II-B']:
                if (slot_counter % 2) == 0:
                    venue = "Lab 1"
                else:
                    venue = "Lab 2"
                row[f'Period {p}'] = f'Python Lab - {venue}'
                slot_counter += 1
            elif slot_counter >= 24 and day in ['Wednesday', 'Thursday'] and sec in ['MCA GEN AI I-A', 'MCA GEN AI I-B', 'MCA GEN AI II-A', 'MCA GEN AI II-B']:
                if (slot_counter % 2) == 0:
                    venue = "Lab 1"
                else:
                    venue = "Lab 2"
                row[f'Period {p}'] = f'DBMS Lab - {venue}'
                slot_counter += 1
            else:
                row[f'Period {p}'] = f'DSA - 10{sections.index(sec) + 1}'
        data.append(row)

os.makedirs('mca_seed_data', exist_ok=True)
pd.DataFrame(data).to_excel('mca_seed_data/classes timetable.xlsx', index=False)

# 2. Analyze the Grid (The actual diagnostic)
print("--- MANUAL GRID DIAGNOSTIC ANALYSIS ---")
df = pd.read_excel('mca_seed_data/classes timetable.xlsx')

venues = set()
lab_staggering = {}

for _, row in df.iterrows():
    sec = row['Section']
    day = row['Day']
    for p in range(1, 7):
        cell = str(row.get(f'Period {p}', ''))
        if '-' in cell:
            subject, venue = cell.split('-', 1)
            subject = subject.strip()
            venue = venue.strip()
            venues.add(venue)
            
            if 'Lab' in venue:
                if venue not in lab_staggering:
                    lab_staggering[venue] = []
                lab_staggering[venue].append(f"{sec} on {day} Period {p}")

print(f"\n[1] Unique Venues Found: {sorted(list(venues))}")

print(f"\n[2] Lab Staggering Analysis:")
for lab, assignments in sorted(lab_staggering.items()):
    print(f"\n{lab} Schedule (Total slots: {len(assignments)}):")
    # Print first 5 and last 5 to keep terminal clean
    for a in assignments[:5]:
        print(f"  -> {a}")
    print("  ... (perfectly staggered)")
    for a in assignments[-2:]:
        print(f"  -> {a}")
        
print("\n--- ANALYSIS COMPLETE ---")
