from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import SessionLocal
from routers.auth import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas
class SubjectUpdate(BaseModel):
    course_code: str
    course_name: str
    programme: str
    regulations: int
    semester: str
    category: str

class FacultyUpdate(BaseModel):
    name: str
    designation: str

class AllocationUpdate(BaseModel):
    faculty_id: int
    subject_id: int
    class_section: str
    theory_hours: float
    practical_hours: float

# Subject Routes
@router.put("/api/management/subjects/{subject_id}")
def update_subject(subject_id: int, payload: SubjectUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    item = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Subject not found")
    item.course_code = payload.course_code
    item.course_name = payload.course_name
    item.programme = payload.programme
    item.regulations = payload.regulations
    item.semester = payload.semester
    item.category = models.SubjectCategoryEnum(payload.category) if hasattr(models.SubjectCategoryEnum, payload.category) else payload.category
    db.commit()
    return {"message": "Subject updated successfully"}

@router.delete("/api/management/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    item = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(item)
    db.commit()
    return {"message": "Subject deleted successfully"}

# Faculty Routes
@router.put("/api/management/faculty/{faculty_id}")
def update_faculty(faculty_id: int, payload: FacultyUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    item = db.query(models.Faculty).filter(models.Faculty.id == faculty_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Faculty not found")
    item.name = payload.name
    item.designation = payload.designation
    db.commit()
    return {"message": "Faculty updated successfully"}

@router.delete("/api/management/faculty/{faculty_id}")
def delete_faculty(faculty_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    item = db.query(models.Faculty).filter(models.Faculty.id == faculty_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Faculty not found")
    db.delete(item)
    db.commit()
    return {"message": "Faculty deleted successfully"}

# Allocation Routes
@router.put("/api/management/allocations/{allocation_id}")
def update_allocation(allocation_id: int, payload: AllocationUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    item = db.query(models.WorkloadAllocation).filter(models.WorkloadAllocation.id == allocation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Allocation not found")
    item.faculty_id = payload.faculty_id
    item.subject_id = payload.subject_id
    item.class_section = payload.class_section
    item.theory_hours = payload.theory_hours
    item.practical_hours = payload.practical_hours
    db.commit()
    return {"message": "Allocation updated successfully"}

@router.delete("/api/management/allocations/{allocation_id}")
def delete_allocation(allocation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    item = db.query(models.WorkloadAllocation).filter(models.WorkloadAllocation.id == allocation_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Allocation not found")
    db.delete(item)
    db.commit()
    return {"message": "Allocation deleted successfully"}
