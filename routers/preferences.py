from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
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
