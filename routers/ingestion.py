from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
import io
import models
from database import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/upload/syllabus")
async def upload_syllabus(file: UploadFile = File(...), db: Session = Depends(get_db)):
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


@router.post("/api/upload/workload")
async def upload_workload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name='wl edit ', skiprows=3)
        
        # Ensure a default user exists for generic faculty creations
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

        allocations_to_insert = []
        
        for _, row in df.iterrows():
            staff_name = row.get('Staff Name')
            subject_code = row.get('Subject Code')
            class_section = row.get('Class & Section')
            theory = row.get('Theory')
            practical = row.get('Practical')
            
            if pd.isna(staff_name) or pd.isna(subject_code):
                continue
                
            staff_name = str(staff_name).strip()
            subject_code = str(subject_code).strip()
            class_section = str(class_section) if pd.notna(class_section) else ""
            
            theory_hrs = float(theory) if pd.notna(theory) else 0.0
            practical_hrs = float(practical) if pd.notna(practical) else 0.0
            
            # Find or create faculty
            faculty = db.query(models.Faculty).filter(models.Faculty.name == staff_name).first()
            if not faculty:
                faculty = models.Faculty(
                    user_id=default_user.id,
                    name=staff_name,
                    designation="Faculty"
                )
                db.add(faculty)
                db.commit()
                db.refresh(faculty)
                
            # Find subject
            subject = db.query(models.Subject).filter(models.Subject.course_code == subject_code).first()
            if not subject:
                # If subject not found, we can't create allocation (Foreign Key constraint)
                # We could create a dummy subject but it's safer to skip or log
                continue
                
            allocation = models.WorkloadAllocation(
                faculty_id=faculty.id,
                subject_id=subject.id,
                class_section=class_section,
                theory_hours=theory_hrs,
                practical_hours=practical_hrs
            )
            allocations_to_insert.append(allocation)
            
        db.add_all(allocations_to_insert)
        db.commit()
        
        return {"message": f"Successfully ingested {len(allocations_to_insert)} workload allocations"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
