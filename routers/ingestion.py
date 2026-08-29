from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
import io
import models
from database import SessionLocal
from routers.auth import get_current_user, verify_admin_role

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/upload/syllabus")
async def upload_syllabus(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name='CD FORMAT ', skiprows=3)
        
        dept = db.query(models.Department).first()
        if not dept:
            dept = models.Department(name="General", programme_scope="Both")
            db.add(dept)
            db.commit()
            db.refresh(dept)
            
        department_id = dept.id
        subjects_to_insert = []
        
        for _, row in df.iterrows():
            course_code = row.get('Course Code')
            course_name = row.get('Course Name')
            programme = row.get('Programme')
            regulations = row.get('Regulations')
            semester = row.get('Semester')
            category_raw = row.get('Course Category')
            
            if pd.isna(course_code):
                continue
                
            subject = models.Subject(
                department_id=department_id,
                course_code=str(course_code),
                course_name=str(course_name) if pd.notna(course_name) else "",
                programme=str(programme) if pd.notna(programme) else "",
                regulations=int(regulations) if pd.notna(regulations) else 2025,
                semester=str(semester) if pd.notna(semester) else "I",
                category=str(category_raw) if pd.notna(category_raw) else "Theory"
            )
            subjects_to_insert.append(subject)

        db.add_all(subjects_to_insert)
        db.commit()
        
        return {"message": f"Successfully ingested {len(subjects_to_insert)} subjects"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/upload/faculty_list")
async def upload_faculty_list(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    try:
        contents = await file.read()
        # Assumes the first sheet is the faculty list if sheet_name not specified, or just reads it
        df = pd.read_excel(io.BytesIO(contents))
        
        default_user = db.query(models.User).filter_by(email="default_faculty@example.com").first()
        if not default_user:
            default_user = models.User(
                email="default_faculty@example.com",
                hashed_password="hashed_password",
                role=models.RoleEnum.FACULTY
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            
        faculty_to_insert = []
        
        for _, row in df.iterrows():
            staff_name = row.get('Staff Name')
            designation = row.get('Designation')
            
            if pd.isna(staff_name):
                continue
                
            staff_name = str(staff_name).strip()
            designation = str(designation).strip() if pd.notna(designation) else "Faculty"
            
            # Avoid duplicates
            existing = db.query(models.Faculty).filter(models.Faculty.name == staff_name).first()
            if not existing:
                faculty = models.Faculty(
                    user_id=default_user.id,
                    name=staff_name,
                    designation=designation
                )
                faculty_to_insert.append(faculty)
                
        db.add_all(faculty_to_insert)
        db.commit()
        
        return {"message": f"Successfully ingested {len(faculty_to_insert)} faculty members"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/upload/rooms")
async def upload_rooms(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        rooms_to_insert = []
        for _, row in df.iterrows():
            room_number = row.get('Room Number')
            is_lab = row.get('Is Lab')
            capacity = row.get('Capacity')
            
            if pd.isna(room_number):
                continue
                
            room = models.Room(
                number=str(room_number).strip(),
                is_lab=bool(is_lab) if pd.notna(is_lab) else False,
                capacity=int(capacity) if pd.notna(capacity) else 60
            )
            rooms_to_insert.append(room)
            
        db.add_all(rooms_to_insert)
        db.commit()
        return {"message": f"Successfully ingested {len(rooms_to_insert)} rooms"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
