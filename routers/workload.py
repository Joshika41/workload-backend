from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import models
from database import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AllocationRequest(BaseModel):
    faculty_id: int
    subject_id: int
    class_section: str
    theory_hours: float
    practical_hours: float

@router.post("/api/workload/allocate")
def allocate_workload(allocation: AllocationRequest, db: Session = Depends(get_db)):
    faculty = db.query(models.Faculty).filter(models.Faculty.id == allocation.faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
        
    subject = db.query(models.Subject).filter(models.Subject.id == allocation.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    new_alloc = models.WorkloadAllocation(
        faculty_id=allocation.faculty_id,
        subject_id=allocation.subject_id,
        class_section=allocation.class_section,
        theory_hours=allocation.theory_hours,
        practical_hours=allocation.practical_hours
    )
    db.add(new_alloc)
    db.commit()
    db.refresh(new_alloc)
    return {"message": "Allocation successfully created", "id": new_alloc.id}

@router.get("/api/workload/summary")
def workload_summary(db: Session = Depends(get_db)):
    faculties = db.query(models.Faculty).all()
    summary = []
    
    for f in faculties:
        total_theory = sum(alloc.theory_hours for alloc in f.allocations)
        total_prac = sum(alloc.practical_hours for alloc in f.allocations)
        summary.append({
            "faculty_id": f.id,
            "name": f.name,
            "designation": f.designation,
            "total_assigned_hours": total_theory + total_prac
        })
        
    return summary
