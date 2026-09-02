
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
import models
from database import SessionLocal, CohortSyllabusMapping, WorkloadAllocation, Syllabus, Cohort, RoleTypeEnum, ProgramTypeEnum, SemesterTypeEnum, Faculty
from routers.auth import verify_admin_role
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CurriculumMapRequest(BaseModel):
    cohort_id: str
    subject_codes: List[str]

@router.post("/api/admin/map-curriculum")
def map_curriculum(
    payload: CurriculumMapRequest,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(verify_admin_role)
):
    try:
        with db.begin_nested():
            # Delete existing mappings for this cohort
            db.query(CohortSyllabusMapping).filter_by(cohort_id=payload.cohort_id).delete()
            
            # Insert new mappings
            mappings = []
            for code in payload.subject_codes:
                m = CohortSyllabusMapping(
                    cohort_id=payload.cohort_id,
                    subject_code=code
                )
                mappings.append(m)
            db.add_all(mappings)
            
        db.commit()
        return {"message": "Curriculum mapped successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


class AllocationSplit(BaseModel):
    faculty_id: str
    role_type: str
    theory_hours: int
    lab_hours: int

class AssignmentRequest(BaseModel):
    cohort_id: str
    subject_code: str
    allocations: List[AllocationSplit]

@router.post("/api/admin/allocations/assign")
def assign_allocation(
    payload: AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(verify_admin_role)
):
    try:
        with db.begin_nested():
            # Get syllabus limits
            syllabus = db.query(Syllabus).filter_by(subject_code=payload.subject_code).first()
            if not syllabus:
                raise HTTPException(status_code=400, detail="Subject not found.")
                
            total_theory_req = syllabus.theory_hours_l or 0
            total_lab_req = syllabus.practical_hours_p or 0
            
            # Calculate new sums
            sum_theory = sum(a.theory_hours for a in payload.allocations)
            sum_lab = sum(a.lab_hours for a in payload.allocations)
            
            if sum_theory > total_theory_req:
                raise HTTPException(status_code=400, detail=f"Allocated theory hours ({sum_theory}) exceed syllabus limit ({total_theory_req}).")
            if sum_lab > total_lab_req:
                raise HTTPException(status_code=400, detail=f"Allocated lab hours ({sum_lab}) exceed syllabus limit ({total_lab_req}).")
                
            # Clear old allocations for this cohort+subject
            db.query(WorkloadAllocation).filter_by(
                cohort_id=payload.cohort_id, 
                subject_code=payload.subject_code
            ).delete()
            
            # Insert new ones
            for alloc in payload.allocations:
                wa = WorkloadAllocation(
                    faculty_id=alloc.faculty_id,
                    subject_code=payload.subject_code,
                    cohort_id=payload.cohort_id,
                    role_type=RoleTypeEnum(alloc.role_type.upper() if alloc.role_type.upper() == 'MAIN' else 'IN-2'),
                    allocated_theory_hours=alloc.theory_hours,
                    allocated_lab_hours=alloc.lab_hours
                )
                db.add(wa)
                
        db.commit()
        return {"message": "Allocations assigned successfully."}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/admin/verify-allocations")
def verify_allocations(
    program_type: str,
    semester_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(verify_admin_role)
):
    prog = ProgramTypeEnum(program_type.upper())
    sem = SemesterTypeEnum(semester_type.upper())
    
    # Get all active cohorts in this workspace
    cohorts = db.query(Cohort).filter_by(program_type=prog, semester_type=sem).all()
    cohort_ids = [c.id for c in cohorts]
    
    # Get mappings
    mappings = db.query(CohortSyllabusMapping).filter(CohortSyllabusMapping.cohort_id.in_(cohort_ids)).all()
    
    is_ready = True
    issues = []
    
    for m in mappings:
        syllabus = db.query(Syllabus).filter_by(subject_code=m.subject_code).first()
        if not syllabus:
            continue
            
        req_theory = syllabus.theory_hours_l or 0
        req_lab = syllabus.practical_hours_p or 0
        
        # Sum allocated
        allocs = db.query(WorkloadAllocation).filter_by(cohort_id=m.cohort_id, subject_code=m.subject_code).all()
        alloc_theory = sum(a.allocated_theory_hours for a in allocs)
        alloc_lab = sum(a.allocated_lab_hours for a in allocs)
        
        if alloc_theory != req_theory or alloc_lab != req_lab:
            is_ready = False
            issues.append({
                "cohort_id": m.cohort_id,
                "subject_code": m.subject_code,
                "theory_discrepancy": req_theory - alloc_theory,
                "lab_discrepancy": req_lab - alloc_lab
            })
            
    return {"is_ready": is_ready, "issues": issues}


@router.get("/api/admin/export-workload")
def export_workload(
    program_type: str,
    semester_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(verify_admin_role)
):
    prog = ProgramTypeEnum(program_type.upper())
    sem = SemesterTypeEnum(semester_type.upper())
    
    # Get allocations for the workspace
    # We join with Cohort to filter by workspace
    allocations = db.query(WorkloadAllocation, Cohort, Syllabus, Faculty).join(
        Cohort, WorkloadAllocation.cohort_id == Cohort.id
    ).join(
        Syllabus, WorkloadAllocation.subject_code == Syllabus.subject_code
    ).join(
        Faculty, WorkloadAllocation.faculty_id == Faculty.faculty_id
    ).filter(
        Cohort.program_type == prog,
        Cohort.semester_type == sem
    ).all()
    
    # Group by faculty_id
    faculty_groups = {}
    for alloc, cohort, syllabus, faculty in allocations:
        fid = faculty.faculty_id
        if fid not in faculty_groups:
            faculty_groups[fid] = {
                "name_formatted": f"{faculty.name} ({faculty.designation or 'Faculty'})",
                "rows": [],
                "total_theory": 0,
                "total_lab": 0
            }
        
        c_title = syllabus.course_title
        if alloc.role_type == RoleTypeEnum.IN2:
            c_title = f"{c_title} [Lab - IN2]"
            
        faculty_groups[fid]["rows"].append([
            c_title,
            syllabus.subject_code,
            f"{cohort.class_name} - {cohort.section}",
            str(alloc.allocated_theory_hours),
            str(alloc.allocated_lab_hours)
        ])
        faculty_groups[fid]["total_theory"] += alloc.allocated_theory_hours
        faculty_groups[fid]["total_lab"] += alloc.allocated_lab_hours
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph(f"Workload Allocation - {program_type.upper()} {semester_type.upper()}", styles['Title']))
    elements.append(Spacer(1, 12))
    
    for fid, group in faculty_groups.items():
        elements.append(Paragraph(group["name_formatted"], styles['Heading2']))
        
        data = [['Course Name', 'Code', 'Class/Sec', 'Theory Hrs', 'Lab Hrs']]
        data.extend(group["rows"])
        data.append(['Total', '', '', str(group["total_theory"]), str(group["total_lab"])])
        
        t = Table(data, style=[
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ])
        elements.append(t)
        elements.append(Spacer(1, 24))
        
    doc.build(elements)
    
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=workload_export_{program_type}_{semester_type}.pdf"
    })
