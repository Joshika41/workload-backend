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
