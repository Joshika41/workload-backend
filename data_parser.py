import pandas as pd
import os
import glob
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class RoomCapacity(BaseModel):
    venue_id: str
    venue_name: str
    type: str
    capacity: int

class FacultyWorkload(BaseModel):
    faculty_id: str
    faculty_name: str
    department: str
    theory_hours: int
    lab_hours: int

class ClassRequirement(BaseModel):
    section: str
    subject: str
    subject_type: str
    hours: int
    faculty_id: str
    required_venue: Optional[str] = None

def parse_seed_data(directory: str = None) -> Dict[str, Any]:
    rooms = []
    workloads = []
    requirements = []
    
    if directory is None:
        directory = os.path.abspath(os.path.join(os.getcwd(), 'mca_seed_data'))
    else:
        directory = os.path.abspath(directory)
        
    print(f"Scanning directory: {directory}")
    
    if not os.path.exists(directory):
        print("Directory does not exist!")
        return {"rooms": rooms, "workloads": workloads, "requirements": requirements}
        
    print(f"Files found: {os.listdir(directory)}")
        
    for filepath in glob.glob(os.path.join(directory, "*.xlsx")):
        filename = os.path.basename(filepath).lower()
        print(f"Reading file: {filepath}")
        df = pd.read_excel(filepath)
        # Normalize headers
        df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_')
        
        # Determine file type heuristically based on columns
        if 'venue_id' in df.columns or 'room_lab_list' in filename:
            for _, row in df.iterrows():
                rooms.append(RoomCapacity(
                    venue_id=str(row.get('venue_id', '')),
                    venue_name=str(row.get('venue_name', '')),
                    type=str(row.get('type', 'Theory')),
                    capacity=int(row.get('capacity', 0)) if pd.notnull(row.get('capacity')) else 0
                ))
        elif 'theory_hours' in df.columns or 'theory' in df.columns or 'workload' in filename:
            for _, row in df.iterrows():
                workloads.append(FacultyWorkload(
                    faculty_id=str(row.get('faculty_id', row.get('id', ''))),
                    faculty_name=str(row.get('faculty_name', row.get('name', ''))),
                    department=str(row.get('department', row.get('dept', ''))),
                    theory_hours=int(row.get('theory_hours', row.get('theory', 0))) if pd.notnull(row.get('theory_hours', row.get('theory'))) else 0,
                    lab_hours=int(row.get('lab_hours', row.get('lab', 0))) if pd.notnull(row.get('lab_hours', row.get('lab'))) else 0
                ))
        elif 'timetable' in filename:
            for _, row in df.iterrows():
                sec = str(row.get('section', row.get('Section', '')))
                if not sec or sec.lower() == 'nan':
                    continue
                for p in range(1, 7):
                    cell = str(row.get(f'Period {p}', row.get(f'period {p}', '')))
                    if cell and cell.lower() != 'nan' and '-' in cell:
                        subject, venue = cell.split('-', 1)
                        subject = subject.strip()
                        venue = venue.strip()
                        sub_type = 'LAB' if 'lab' in subject.lower() else 'THEORY'
                        
                        found = False
                        for req in requirements:
                            if req.section == sec and req.subject == subject:
                                req.hours += 1
                                req.required_venue = venue
                                found = True
                                break
                        if not found:
                            requirements.append(ClassRequirement(
                                section=sec,
                                subject=subject,
                                subject_type=sub_type,
                                hours=1,
                                faculty_id='FAC1', # Default
                                required_venue=venue
                            ))
        else:
            # Assume class requirements/timetable
            for _, row in df.iterrows():
                requirements.append(ClassRequirement(
                    section=str(row.get('section', '')),
                    subject=str(row.get('subject', '')),
                    subject_type=str(row.get('subject_type', row.get('type', 'Theory'))),
                    hours=int(row.get('hours', 0)) if pd.notnull(row.get('hours')) else 0,
                    faculty_id=str(row.get('faculty_id', '')),
                    required_venue=str(row.get('required_venue', '')) if 'required_venue' in row else None
                ))
                
    return {
        "rooms": rooms,
        "workloads": workloads,
        "requirements": requirements
    }
