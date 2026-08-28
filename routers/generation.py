from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ortools.sat.python import cp_model
import models
from database import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/generate/timetables")
def generate_timetables(db: Session = Depends(get_db)):
    allocations = db.query(models.WorkloadAllocation).join(models.Faculty).join(models.Subject).all()
    rooms = db.query(models.Room).all()
    
    if not allocations:
        raise HTTPException(status_code=400, detail="No workload allocations found.")
    if not rooms:
        raise HTTPException(status_code=400, detail="No rooms found.")
        
    model = cp_model.CpModel()
    
    num_days = 5
    num_periods = 6
    
    # vars[allocation_id][day][period][room_id]
    assignments = {}
    for alloc in allocations:
        assignments[alloc.id] = {}
        for d in range(num_days):
            assignments[alloc.id][d] = {}
            for p in range(num_periods):
                assignments[alloc.id][d][p] = {}
                for r in rooms:
                    assignments[alloc.id][d][p][r.id] = model.NewBoolVar(f'assign_{alloc.id}_{d}_{p}_{r.id}')
                    
    # Faculty teaches one subject per period
    faculty_allocs = {}
    for alloc in allocations:
        if alloc.faculty_id not in faculty_allocs:
            faculty_allocs[alloc.faculty_id] = []
        faculty_allocs[alloc.faculty_id].append(alloc.id)
        
    for fac_id, alloc_ids in faculty_allocs.items():
        for d in range(num_days):
            for p in range(num_periods):
                model.Add(sum(assignments[a_id][d][p][r.id] for a_id in alloc_ids for r in rooms) <= 1)
                
    # Class section attends one subject per period
    section_allocs = {}
    for alloc in allocations:
        if alloc.class_section not in section_allocs:
            section_allocs[alloc.class_section] = []
        section_allocs[alloc.class_section].append(alloc.id)
        
    for sec, alloc_ids in section_allocs.items():
        for d in range(num_days):
            for p in range(num_periods):
                model.Add(sum(assignments[a_id][d][p][r.id] for a_id in alloc_ids for r in rooms) <= 1)
                
    # Room hosts one class per period
    for d in range(num_days):
        for p in range(num_periods):
            for r in rooms:
                model.Add(sum(assignments[alloc.id][d][p][r.id] for alloc in allocations) <= 1)
                
    # Fulfill exact theory and practical hours
    for alloc in allocations:
        total_required = int(alloc.theory_hours + alloc.practical_hours)
        model.Add(sum(assignments[alloc.id][d][p][r.id] 
                      for d in range(num_days) 
                      for p in range(num_periods) 
                      for r in rooms) == total_required)
                      
    # Elective Block Scheduling
    electives_by_sem = {}
    for alloc in allocations:
        # Safely extract value if enum
        cat_val = alloc.subject.category.value if hasattr(alloc.subject.category, 'value') else alloc.subject.category
        if cat_val == "Elective":
            sem = alloc.subject.semester
            if sem not in electives_by_sem:
                electives_by_sem[sem] = []
            electives_by_sem[sem].append(alloc)
            
    for sem, elecs in electives_by_sem.items():
        if len(elecs) > 1:
            for i in range(1, len(elecs)):
                alloc1 = elecs[0]
                alloc2 = elecs[i]
                for d in range(num_days):
                    for p in range(num_periods):
                        b1 = model.NewBoolVar(f'elec1_{alloc1.id}_{d}_{p}')
                        model.Add(b1 == sum(assignments[alloc1.id][d][p][r.id] for r in rooms))
                        
                        b2 = model.NewBoolVar(f'elec2_{alloc2.id}_{d}_{p}')
                        model.Add(b2 == sum(assignments[alloc2.id][d][p][r.id] for r in rooms))
                        
                        model.Add(b1 == b2)
                        
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        return {"message": "Timetable successfully generated", "status": "optimal" if status == cp_model.OPTIMAL else "feasible"}
    else:
        raise HTTPException(status_code=400, detail="Infeasible: No valid timetable could be generated with these constraints.")
