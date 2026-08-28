from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import pandas as pd
import tempfile
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

@router.get("/api/export/timetable")
def export_timetable(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    schedules = db.query(models.GeneratedTimetable).all()
    
    if not schedules:
        raise HTTPException(status_code=404, detail="No generated timetable found to export.")
        
    data = []
    for s in schedules:
        alloc = s.allocation
        data.append({
            "Day": s.day,
            "Period": s.period,
            "Class Section": alloc.class_section,
            "Subject": alloc.subject.course_name,
            "Faculty": alloc.faculty.name,
            "Room": s.room.number
        })
        
    df = pd.DataFrame(data)
    
    # Create an empty matrix: Days (Y) x Periods (X) for each Class Section
    # We can use pandas pivot_table to quickly build this
    # A single cell contains "Subject - Faculty (Room)"
    
    df["Details"] = df["Subject"] + " - " + df["Faculty"] + " (" + df["Room"] + ")"
    
    pivot_df = df.pivot_table(
        index=["Class Section", "Day"],
        columns="Period",
        values="Details",
        aggfunc=lambda x: ' | '.join(x)
    ).reset_index()
    
    # Save to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    pivot_df.to_excel(temp_file.name, index=False)
    
    return FileResponse(
        temp_file.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="university_timetable.xlsx"
    )
