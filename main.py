import os
from dotenv import load_dotenv
load_dotenv()

import io
import pandas as pd
import sqlite3
import jwt
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import SessionLocal, Faculty, Room, Syllabus, WorkloadConfiguration, User, FacultyPreference, TimetableBlock
from auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from datetime import timedelta
from solver import solve_timetable
from data_parser import parse_seed_data

import models
from database import engine
from routers.ingestion import router as ingestion_router
from routers.generation import router as generation_router
from routers.workload import router as workload_router
from routers.preferences import router as preferences_router
from routers.auth import router as auth_router
from routers.management import router as management_router
from routers.export import router as export_router

app = FastAPI(title="University Timetable Admin API")

models.Base.metadata.create_all(bind=engine)
app.include_router(ingestion_router)
app.include_router(generation_router)
app.include_router(workload_router)
app.include_router(preferences_router)
app.include_router(auth_router)
app.include_router(management_router)
app.include_router(export_router)


# --- CORS Middleware Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, adjust in production if necessary
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---

class FacultyListResponse(BaseModel):
    id: str
    name: str
    department: str
    theory_hours: int = 0
    lab_hours: int = 0
    incharge_hours: int = 0
    max_hours_limit: int = 16

class FacultyWorkloadConfig(BaseModel):
    faculty_id: str
    department: str
    theory_hours: int
    lab_hours: int
    incharge_hours: int
    max_hours_limit: int

class FacultyWorkloadResponse(BaseModel):
    faculty_id: str
    department: str
    theory_hours: int
    lab_hours: int
    incharge_hours: int
    max_hours_limit: int
    total_calculated: int
    is_overloaded: bool
    validation_status: str
    warning_message: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class PreferenceSubmission(BaseModel):
    subjects: List[str]

class EditBlockRequest(BaseModel):
    day: int
    period: int

# --- Auth Dependencies ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- Routes ---

@app.post("/api/auth/login")
def login_for_access_token(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value, "faculty_id": user.faculty_id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/faculty/preferences")
def submit_preferences(req: PreferenceSubmission, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "FACULTY":
        raise HTTPException(status_code=403, detail="Only faculty can submit preferences.")
    
    faculty_id = current_user.faculty_id
    if not faculty_id:
        raise HTTPException(status_code=400, detail="User is not linked to a faculty profile.")

    # Delete existing preferences for this faculty if they re-submit
    db.query(FacultyPreference).filter(FacultyPreference.faculty_id == faculty_id).delete()
    
    # Insert new preferences
    for subject in req.subjects:
        new_pref = FacultyPreference(
            faculty_id=faculty_id,
            subject_name=subject,
            status="PENDING"
        )
        db.add(new_pref)
        
    db.commit()
    return {"message": "Preferences submitted successfully", "count": len(req.subjects)}

@app.get("/api/syllabus")
def get_syllabus(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    syllabus_items = db.query(Syllabus).all()
    results = []
    for s in syllabus_items:
        results.append({
            "course_code": s.course_code,
            "course_title": s.course_title,
            "course_type": s.course_type,
            "category": s.category
        })
    return results

@app.get("/api/admin/preferences")
def get_all_preferences(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can view all preferences.")
        
    prefs = db.query(FacultyPreference).all()
    # Format the response logically
    results = []
    for p in prefs:
        results.append({
            "id": p.id,
            "faculty_id": p.faculty_id,
            "subject_name": p.subject_name,
            "status": p.status
        })
    return results

@app.put("/api/admin/preferences/{pref_id}/approve")
def approve_preference(pref_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can approve preferences.")
        
    pref = db.query(FacultyPreference).filter(FacultyPreference.id == pref_id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found.")
        
    pref.status = "APPROVED"
    db.commit()
    
    return {
        "id": pref.id,
        "faculty_id": pref.faculty_id,
        "subject_name": pref.subject_name,
        "status": pref.status
    }

@app.put("/api/admin/preferences/{pref_id}/reject")
def reject_preference(pref_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can reject preferences.")
        
    pref = db.query(FacultyPreference).filter(FacultyPreference.id == pref_id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found.")
        
    pref.status = "REJECTED"
    db.commit()
    
    return {
        "id": pref.id,
        "faculty_id": pref.faculty_id,
        "subject_name": pref.subject_name,
        "status": pref.status
    }

@app.get("/api/admin/faculty-list")
def get_faculty_list(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can view faculty list.")
    try:
        with sqlite3.connect("university_timetable.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, department FROM faculty")
            rows = cursor.fetchall()
            
        return [
            {
                "faculty_id": r[0],
                "name": r[1],
                "department": r[2],
                "theory_hours": 0,
                "lab_hours": 0,
                "incharge_hours": 0,
                "max_hours_limit": 16
            } for r in rows
        ]
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/admin/generate-workload")
def generate_workload(configs: List[FacultyWorkloadConfig], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Takes an array of configured faculty configurations, runs the mathematical 
    workload calculation equation, checks for workload overflows, and saves 
    the result to the database before returning the validation status.
    """
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can generate workload.")
        
    results = []
    try:
        for config in configs:
            total_calculated = config.theory_hours + config.lab_hours + config.incharge_hours
            is_overloaded = total_calculated > config.max_hours_limit
            
            # Database Persistence
            existing_record = db.query(WorkloadConfiguration).filter(WorkloadConfiguration.faculty_id == config.faculty_id).first()
            
            if existing_record:
                existing_record.theory_hours = config.theory_hours
                existing_record.lab_hours = config.lab_hours
                existing_record.incharge_hours = config.incharge_hours
                existing_record.max_hours_limit = config.max_hours_limit
                existing_record.total_calculated_hours = total_calculated
                existing_record.is_overloaded = is_overloaded
            else:
                new_record = WorkloadConfiguration(
                    faculty_id=config.faculty_id,
                    theory_hours=config.theory_hours,
                    lab_hours=config.lab_hours,
                    incharge_hours=config.incharge_hours,
                    max_hours_limit=config.max_hours_limit,
                    total_calculated_hours=total_calculated,
                    is_overloaded=is_overloaded
                )
                db.add(new_record)
            
            warning_message = None
            validation_status = "Valid"
            
            if is_overloaded:
                warning_message = f"Warning: Faculty {config.faculty_id} exceeds the maximum limit of {config.max_hours_limit} hours by {total_calculated - config.max_hours_limit} hour(s)."
                validation_status = "Overloaded"
                
            response_item = FacultyWorkloadResponse(
                faculty_id=config.faculty_id,
                department=config.department,
                theory_hours=config.theory_hours,
                lab_hours=config.lab_hours,
                incharge_hours=config.incharge_hours,
                max_hours_limit=config.max_hours_limit,
                total_calculated=total_calculated,
                is_overloaded=is_overloaded,
                validation_status=validation_status,
                warning_message=warning_message
            )
            results.append(response_item)
            
        db.commit()
        
        # --- PHASE 3: TIMETABLE GENERATION ---
        workload_data = []
        prefs = db.query(FacultyPreference).filter(FacultyPreference.status == "APPROVED").all()
        print(f"STEP 1: Fetching APPROVED preferences... Found: {len(prefs)}")
        
        for pref in prefs:
            sub_type = "LAB" if "Lab" in pref.subject_name or "Practical" in pref.subject_name else "THEORY"
            hours = 2 if sub_type == "LAB" else 3
            workload_data.append({
                'faculty_id': pref.faculty_id,
                'section': 'A',  # Hardcoded Section A for POC
                'subject': pref.subject_name,
                'hours': hours,
                'type': sub_type
            })
            
        print(f"STEP 2: Solver payload formatted... Payload: {workload_data}")
        
        classes = ['A']
        timetable_result = solve_timetable(workload_data, classes)
        
        print(f"STEP 3: Engine executed... Status returned: {timetable_result['status']}")
        
        if timetable_result['status'] in ['OPTIMAL', 'FEASIBLE']:
            db.query(TimetableBlock).delete()
            new_blocks = []
            for block in timetable_result['blocks']:
                new_block = TimetableBlock(
                    faculty_id=block['faculty_id'],
                    section=block['section'],
                    subject=block['subject'],
                    day=block['day'],
                    period=block['period']
                )
                new_blocks.append(new_block)
            
            db.add_all(new_blocks)
            db.commit()
            for b in new_blocks:
                db.refresh(b)
            
        return {
            "message": "Timetable generated successfully.",
            "status": timetable_result['status'],
            "total_blocks": len(timetable_result['blocks']) if timetable_result['status'] in ['OPTIMAL', 'FEASIBLE'] else 0,
            "workload": results
        }
    except Exception as e:
        print(f"RAW EXCEPTION IN PIPELINE: {repr(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to generate workload: {str(e)}")

@app.post("/api/admin/generate-test")
async def generate_test_timetable(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can generate timetables.")
        
    # Hardcoded mock scenario: Dr. Anandan (FAC001) teaching CS104 to Section A for 3 hours, and a 2 hour Lab.
    mock_workload = [
        {'faculty_id': 'FAC001', 'section': 'A', 'subject': 'CS104', 'hours': 3, 'type': 'THEORY'},
        {'faculty_id': 'FAC001', 'section': 'A', 'subject': 'CS105-Lab', 'hours': 2, 'type': 'LAB'}
    ]
    mock_classes = ['A']
    
    result = await run_in_threadpool(solve_timetable, mock_workload, mock_classes)
    return result

@app.post("/api/admin/generate-batch")
async def generate_batch(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can run batch generation.")
        
    parsed_data = parse_seed_data()
    requirements = parsed_data.get("requirements", [])
    rooms = parsed_data.get("rooms", [])
    
    if not requirements:
        raise HTTPException(status_code=400, detail="No class requirements found in seed data.")
        
    workload_data = []
    classes = set()
    for req in requirements:
        workload_data.append({
            'faculty_id': req.faculty_id,
            'section': req.section,
            'subject': req.subject,
            'hours': req.hours,
            'type': req.subject_type,
            'required_venue': req.required_venue
        })
        classes.add(req.section)
        
    result = await run_in_threadpool(solve_timetable, workload_data, list(classes), rooms)
    
    if result['status'] in ['OPTIMAL', 'FEASIBLE']:
        db.query(TimetableBlock).delete()
        for block in result['blocks']:
            new_block = TimetableBlock(
                faculty_id=block['faculty_id'],
                section=block['section'],
                subject=block['subject'],
                day=block['day'],
                period=block['period']
            )
            db.add(new_block)
        db.commit()
        
    return {
        "message": f"Batch generation complete. Engine Status: {result['status']}",
        "status": result['status'],
        "total_blocks": len(result['blocks']) if result['status'] in ['OPTIMAL', 'FEASIBLE'] else 0
    }

@app.get("/api/admin/timetable")
def get_timetable(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can view the timetable.")
        
    blocks = db.query(TimetableBlock).all()
    results = []
    for block in blocks:
        results.append({
            "id": block.id,
            "faculty_id": block.faculty_id,
            "section": block.section,
            "subject": block.subject,
            "day": block.day,
            "period": block.period
        })
    return results

@app.put("/api/admin/timetable/{block_id}")
def update_timetable_block(block_id: int, req: EditBlockRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can edit blocks.")
        
    block = db.query(TimetableBlock).filter(TimetableBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
        
    block.day = req.day
    block.period = req.period
    db.commit()
    db.refresh(block)
    return {
        "id": block.id,
        "faculty_id": block.faculty_id,
        "section": block.section,
        "subject": block.subject,
        "day": block.day,
        "period": block.period
    }

@app.get("/api/timetable/metadata")
def get_metadata(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Accessible to ADMIN and FACULTY
    departments = [r[0] for r in db.query(Faculty.department).filter(Faculty.department != None).distinct().all()]
    sections = [r[0] for r in db.query(TimetableBlock.section).filter(TimetableBlock.section != None).distinct().all()]
    faculty_ids = [r[0] for r in db.query(Faculty.id).filter(Faculty.id != None).distinct().all()]
    
    return {
        "departments": departments,
        "sections": sections,
        "faculty_ids": faculty_ids
    }

@app.get("/api/faculty/timetable")
def get_faculty_timetable(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "FACULTY":
        raise HTTPException(status_code=403, detail="Only faculty can view personal schedules here.")
        
    fac_id = current_user.faculty_id
    if not fac_id:
        raise HTTPException(status_code=400, detail="User is not linked to a faculty profile.")
        
    personal_blocks = db.query(TimetableBlock).filter(TimetableBlock.faculty_id == fac_id).all()
    
    faculty_sections = [r[0] for r in db.query(TimetableBlock.section).filter(TimetableBlock.faculty_id == fac_id).distinct().all()]
    class_blocks = db.query(TimetableBlock).filter(TimetableBlock.section.in_(faculty_sections)).all() if faculty_sections else []
    
    class_schedules = {}
    for b in class_blocks:
        if b.section not in class_schedules:
            class_schedules[b.section] = []
        class_schedules[b.section].append({
            "id": b.id,
            "faculty_id": b.faculty_id,
            "subject": b.subject,
            "day": b.day,
            "period": b.period
        })
        
    personal_schedule = [{
        "id": b.id,
        "faculty_id": b.faculty_id,
        "subject": b.subject,
        "day": b.day,
        "period": b.period,
        "section": b.section
    } for b in personal_blocks]
        
    return {
        "personal_schedule": personal_schedule,
        "class_schedules": class_schedules
    }

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Helper function to clean up Pandas DataFrames parsed from Excel."""
    df = df.dropna(how='all')
    
    # Strip whitespace, lowercase, and replace spaces with underscores for headers
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace(' ', '_')
    
    # Alias Mapping Dictionary for extreme resilience
    alias_map = {
        'facultyid': 'faculty_id',
        'id': 'faculty_id',
        'faculty_name': 'name',
        'dept': 'department',
        'limit': 'max_hours_limit',
        'max_hours': 'max_hours_limit',
        'max_limit': 'max_hours_limit',
        'theory': 'theory_hours',
        'lab': 'lab_hours',
        'incharge': 'incharge_hours'
    }
    df = df.rename(columns=alias_map)
    
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.strip()
        
    df = df.where(pd.notnull(df), None)
    return df

@app.post("/api/admin/upload-metadata")
async def upload_metadata(
    syllabus_file: Optional[UploadFile] = File(None),
    faculty_file: Optional[UploadFile] = File(None),
    rooms_file: Optional[UploadFile] = File(None),
    total_hours_file: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    type: Optional[str] = Form(None),
    file_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can upload metadata.")
        
    try:
        parsed_results = {}

        def process_df(df, hint=None):
            cols = list(df.columns)
            if 'course_code' in cols or hint == 'syllabus':
                db.query(Syllabus).delete()
                # Drop rows where course_code is missing
                df = df.dropna(subset=['course_code']) if 'course_code' in df.columns else df
                for _, row in df.iterrows():
                    if row.get('course_code'):
                        db.add(Syllabus(
                            course_code=str(row.get('course_code')),
                            course_title=str(row.get('course_title', '')),
                            course_type=str(row.get('course_type', '')),
                            category=str(row.get('category', ''))
                        ))
            elif 'room_number' in cols or hint == 'rooms':
                db.query(Room).delete()
                df = df.dropna(subset=['room_number']) if 'room_number' in df.columns else df
                for _, row in df.iterrows():
                    if row.get('room_number'):
                        capacity = row.get('capacity', 0)
                        db.add(Room(
                            room_number=str(row.get('room_number')),
                            room_type=str(row.get('room_type', '')),
                            capacity=int(capacity) if pd.notnull(capacity) else 0
                        ))
            elif 'max_hours_limit' in cols or hint == 'total_hours':
                db.query(WorkloadConfiguration).delete()
                df = df.dropna(subset=['faculty_id']) if 'faculty_id' in df.columns else df
                for _, row in df.iterrows():
                    if row.get('faculty_id'):
                        max_limit = row.get('max_hours_limit', 16)
                        db.add(WorkloadConfiguration(
                            faculty_id=str(row.get('faculty_id')),
                            max_hours_limit=int(max_limit) if pd.notnull(max_limit) else 16
                        ))
            elif 'name' in cols and 'faculty_id' in cols or hint == 'faculty':
                db.query(Faculty).delete()
                df = df.dropna(subset=['faculty_id']) if 'faculty_id' in df.columns else df
                
                faculty_list = []
                for _, row in df.iterrows():
                    f_id = row.get('faculty_id')
                    if f_id:
                        fac = Faculty(
                            id=str(f_id),
                            name=str(row.get('name', '')),
                            department=str(row.get('department', ''))
                        )
                        db.add(fac)
                        faculty_list.append({
                            "faculty_id": str(f_id),
                            "name": str(row.get('name', '')),
                            "department": str(row.get('department', '')),
                            "theory_hours": 0,
                            "lab_hours": 0,
                            "incharge_hours": 0,
                            "max_hours_limit": 16
                        })
                parsed_results["faculty"] = faculty_list

        files_to_process = [
            (syllabus_file, 'syllabus'),
            (faculty_file, 'faculty'),
            (rooms_file, 'rooms'),
            (total_hours_file, 'total_hours'),
            (file, type or file_type)
        ]
        
        for f, hint in files_to_process:
            if f:
                process_df(clean_dataframe(pd.read_excel(io.BytesIO(await f.read()))), hint)

        db.commit()

        # Update returned max_hours_limit from the newly inserted WorkloadConfigurations
        if "faculty" in parsed_results:
            limits = {w.faculty_id: w.max_hours_limit for w in db.query(WorkloadConfiguration).all()}
            for f in parsed_results["faculty"]:
                f["max_hours_limit"] = limits.get(f["faculty_id"], 16)

        return {
            "message": "Successfully processed and uploaded metadata.", 
            "success": True,
            **parsed_results
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to process files: {str(e)}")
