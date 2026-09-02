from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import models
from database import SessionLocal

from database import Syllabus, PreferenceConstraint, SubjectPreference, ProgramTypeEnum, SemesterTypeEnum, Faculty

from routers.auth import get_current_user, verify_admin_role

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PreferenceRequest(BaseModel):
    faculty_id: int
    preferred_day: str
    preferred_period: int
    preference_type: str 

@router.post("/api/faculty/preferences")
def submit_preferences(prefs: List[PreferenceRequest], db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        if not prefs:
            return {"message": "No preferences submitted"}
            
        fac_id = prefs[0].faculty_id
        db.query(models.FacultyPreference).filter(models.FacultyPreference.faculty_id == fac_id).delete()
        
        pref_records = []
        for p in prefs:
            pref_records.append(models.FacultyPreference(
                faculty_id=p.faculty_id,
                preferred_day=p.preferred_day,
                preferred_period=p.preferred_period,
                preference_type=models.PreferenceTypeEnum(p.preference_type)
            ))
            
        db.add_all(pref_records)
        db.commit()
        return {"message": f"Successfully saved {len(pref_records)} preferences"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/admin/preferences")
def get_all_preferences(db: Session = Depends(get_db), current_user: models.User = Depends(verify_admin_role)):
    prefs = db.query(models.FacultyPreference).join(models.Faculty).all()
    
    result = []
    for p in prefs:
        result.append({
            "id": p.id,
            "faculty_name": p.faculty.name,
            "faculty_id": p.faculty_id,
            "preferred_day": p.preferred_day,
            "preferred_period": p.preferred_period,
            "preference_type": p.preference_type.value if hasattr(p.preference_type, 'value') else p.preference_type
        })
        
    return result


@router.get("/api/faculty/form-data")
def get_faculty_form_data(
    program_type: str, 
    semester_type: str, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    prog = ProgramTypeEnum(program_type.upper())
    sem = SemesterTypeEnum(semester_type.upper())
    
    # User's faculty info
    # (Assuming current_user has a related Faculty record, or we can look it up)
    faculty_rec = db.query(Faculty).filter_by(faculty_id=current_user.username).first()
    
    # Filter syllabus by program_type, semester_type, and active status
    # As Syllabus does not directly contain a department column in the current schema,
    # we return all available subjects for the workspace.
    syllabus_records = db.query(Syllabus).filter_by(
        program_type=prog, 
        semester_type=sem,
        is_active=True
    ).all()
    
    return {
        "faculty_department": faculty_rec.department if faculty_rec else None,
        "subjects": [
            {
                "subject_code": s.subject_code,
                "course_title": s.course_title,
                "subject_category": s.subject_category,
                "theory_hours_l": s.theory_hours_l,
                "practical_hours_p": s.practical_hours_p,
                "credits_c": s.credits_c
            } for s in syllabus_records
        ]
    }

class CartSubmissionRequest(BaseModel):
    program_type: str
    semester_type: str
    subject_codes: List[str]

@router.post("/api/faculty/submit-cart")
def submit_faculty_cart(
    payload: CartSubmissionRequest,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    try:
        prog = ProgramTypeEnum(payload.program_type.upper())
        sem = SemesterTypeEnum(payload.semester_type.upper())
        faculty_id = current_user.username
        
        if not payload.subject_codes:
            raise HTTPException(status_code=400, detail="Cart is empty.")
            
        with db.begin_nested():
            # Group submitted subjects by category
            subjects = db.query(Syllabus).filter(Syllabus.subject_code.in_(payload.subject_codes)).all()
            if len(subjects) != len(payload.subject_codes):
                raise HTTPException(status_code=400, detail="One or more subject codes are invalid.")
                
            category_counts = {}
            for s in subjects:
                cat = s.subject_category or "Uncategorized"
                category_counts[cat] = category_counts.get(cat, 0) + 1
                
            # Query active constraints
            constraints = db.query(PreferenceConstraint).filter_by(
                program_type=prog, 
                semester_type=sem
            ).all()
            
            constraint_dict = {c.subject_category: c.max_allowed for c in constraints}
            
            # Validate
            for cat, count in category_counts.items():
                max_allowed = constraint_dict.get(cat)
                if max_allowed is not None and count > max_allowed:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Maximum allowed '{cat}' subjects exceeded. Allowed: {max_allowed}, Submitted: {count}."
                    )
            
            # Delete old pending cart if any for this workspace? 
            # Or just clear all previous pending carts for this faculty?
            # We'll clear the current subject preferences for this faculty.
            db.query(SubjectPreference).filter_by(faculty_id=faculty_id).delete()
            
            # Insert new ones
            for sc in payload.subject_codes:
                pref = SubjectPreference(
                    faculty_id=faculty_id,
                    subject_code=sc,
                    status='PENDING'
                )
                db.add(pref)
                
        db.commit()
        return {"message": "Cart submitted successfully and is pending approval."}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

