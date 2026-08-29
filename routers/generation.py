from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import SessionLocal, GenerationTask
import models
from routers.auth import get_current_user
from ortools.sat.python import cp_model
import json

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_solver_task(task_id: str):
    db = SessionLocal()
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        db.close()
        return
        
    task.status = "PROCESSING"
    db.commit()
    
    try:
        allocations = db.query(models.WorkloadAllocation).join(models.Faculty).join(models.Subject).all()
        rooms = db.query(models.Room).all()
        time_slots = db.query(models.TimeSlot).all()
        
        if not allocations:
            raise Exception("No workload allocations found.")
        if not rooms:
            raise Exception("No rooms found.")
        if not time_slots:
            raise Exception("No time slots configured. Please add time slots.")
            
        model = cp_model.CpModel()
        
        days = sorted(list(set(ts.day_of_week for ts in time_slots)))
        periods = sorted(list(set(ts.period_number for ts in time_slots)))
        
        num_days = len(days)
        num_periods = len(periods)
        
        is_break_map = {}
        for ts in time_slots:
            is_break_map[(ts.day_of_week, ts.period_number)] = ts.is_break
        
        assignments = {}
        is_theory = {}
        is_practical = {}
        prac_starts = {}
        
        for alloc in allocations:
            assignments[alloc.id] = {}
            is_theory[alloc.id] = {}
            is_practical[alloc.id] = {}
            prac_starts[alloc.id] = {}
            
            for d in days:
                assignments[alloc.id][d] = {}
                is_theory[alloc.id][d] = {}
                is_practical[alloc.id][d] = {}
                prac_starts[alloc.id][d] = {}
                
                for p_idx, p in enumerate(periods):
                    assignments[alloc.id][d][p] = {}
                    is_theory[alloc.id][d][p] = {}
                    is_practical[alloc.id][d][p] = {}
                    prac_starts[alloc.id][d][p] = {}
                    
                    for r in rooms:
                        assignments[alloc.id][d][p][r.id] = model.NewBoolVar(f'assign_{alloc.id}_{d}_{p}_{r.id}')
                        is_theory[alloc.id][d][p][r.id] = model.NewBoolVar(f'theory_{alloc.id}_{d}_{p}_{r.id}')
                        is_practical[alloc.id][d][p][r.id] = model.NewBoolVar(f'prac_{alloc.id}_{d}_{p}_{r.id}')
                        
                        if p_idx < num_periods - 1:
                            prac_starts[alloc.id][d][p][r.id] = model.NewBoolVar(f'prac_start_{alloc.id}_{d}_{p}_{r.id}')
                        else:
                            prac_starts[alloc.id][d][p][r.id] = model.NewConstant(0)
                            
                        model.Add(assignments[alloc.id][d][p][r.id] == is_theory[alloc.id][d][p][r.id] + is_practical[alloc.id][d][p][r.id])
                        
                        if is_break_map.get((d, p), False):
                            model.Add(assignments[alloc.id][d][p][r.id] == 0)
                            
        for alloc in allocations:
            for d in days:
                for p_idx, p in enumerate(periods):
                    for r in rooms:
                        prev_start = prac_starts[alloc.id][d][periods[p_idx-1]][r.id] if p_idx > 0 else 0
                        curr_start = prac_starts[alloc.id][d][p][r.id]
                        model.Add(is_practical[alloc.id][d][p][r.id] == curr_start + prev_start)
                        
                        if alloc.practical_hours == 0:
                            model.Add(is_practical[alloc.id][d][p][r.id] == 0)

            practical_hrs = int(alloc.practical_hours)
            if practical_hrs > 0:
                total_prac_starts = sum(prac_starts[alloc.id][d][p][r.id] for d in days for p in periods for r in rooms)
                model.Add(total_prac_starts == practical_hrs // 2)

        faculty_allocs = {}
        for alloc in allocations:
            if alloc.faculty_id not in faculty_allocs:
                faculty_allocs[alloc.faculty_id] = []
            faculty_allocs[alloc.faculty_id].append(alloc.id)
            
        for fac_id, alloc_ids in faculty_allocs.items():
            for d in days:
                for p in periods:
                    model.Add(sum(assignments[a_id][d][p][r.id] for a_id in alloc_ids for r in rooms) <= 1)
                    
            total_assignments = sum(assignments[a_id][d][p][r.id] for a_id in alloc_ids for d in days for p in periods for r in rooms)
            model.Add(total_assignments <= (num_days * num_periods) - 1)
                    
        section_allocs = {}
        for alloc in allocations:
            if alloc.class_section not in section_allocs:
                section_allocs[alloc.class_section] = []
            section_allocs[alloc.class_section].append(alloc.id)
            
        for sec, alloc_ids in section_allocs.items():
            for d in days:
                for p in periods:
                    model.Add(sum(assignments[a_id][d][p][r.id] for a_id in alloc_ids for r in rooms) <= 1)
                    
        for d in days:
            for p in periods:
                for r in rooms:
                    model.Add(sum(assignments[alloc.id][d][p][r.id] for alloc in allocations) <= 1)
                    
        for alloc in allocations:
            total_required_theory = int(alloc.theory_hours)
            model.Add(sum(is_theory[alloc.id][d][p][r.id] 
                          for d in days 
                          for p in periods 
                          for r in rooms) == total_required_theory)
                          
            for d in days:
                model.Add(sum(is_theory[alloc.id][d][p][r.id] for p in periods for r in rooms) <= 2)
                          
        electives_by_sem = {}
        for alloc in allocations:
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
                    for d in days:
                        for p in periods:
                            b1 = model.NewBoolVar(f'elec1_{alloc1.id}_{d}_{p}')
                            model.Add(b1 == sum(assignments[alloc1.id][d][p][r.id] for r in rooms))
                            
                            b2 = model.NewBoolVar(f'elec2_{alloc2.id}_{d}_{p}')
                            model.Add(b2 == sum(assignments[alloc2.id][d][p][r.id] for r in rooms))
                            
                            model.Add(b1 == b2)
                            
        penalties = []
        first_p = periods[0]
        last_p = periods[-1]
        for alloc in allocations:
            for d in days:
                for r in rooms:
                    penalties.append(is_theory[alloc.id][d][first_p][r.id])
                    penalties.append(is_theory[alloc.id][d][last_p][r.id])
                    
        preferences = db.query(models.FacultyPreference).all()
        for pref in preferences:
            cat_val = pref.preference_type.value if hasattr(pref.preference_type, 'value') else pref.preference_type
            if cat_val == "AVOID":
                d_pref = pref.preferred_day
                try:
                    p_pref = int(pref.preferred_period)
                except ValueError:
                    continue
                    
                if d_pref in days and p_pref in periods:
                    for alloc in allocations:
                        if alloc.faculty_id == pref.faculty_id:
                            for r in rooms:
                                penalties.append(assignments[alloc.id][d_pref][p_pref][r.id] * 10) 

        model.Minimize(sum(penalties))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 15.0
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            db.query(models.GeneratedTimetable).delete() 
            
            schedule_inserts = []
            for alloc in allocations:
                for d in days:
                    for p in periods:
                        for r in rooms:
                            if solver.Value(assignments[alloc.id][d][p][r.id]) == 1:
                                schedule_inserts.append(models.GeneratedTimetable(
                                    allocation_id=alloc.id,
                                    day=str(d),
                                    period=int(p),
                                    room_id=r.id
                                ))
                                
            db.add_all(schedule_inserts)
            db.commit()
            task.status = "COMPLETED"
            task.result_payload = {"message": "Timetable successfully generated and saved to database", "status": "optimal" if status == cp_model.OPTIMAL else "feasible"}
        else:
            task.status = "FAILED"
            task.result_payload = {"detail": "Schedule mathematically impossible. Please adjust faculty hours, room constraints, or preferences."}
        db.commit()
    except Exception as e:
        db.rollback()
        task.status = "FAILED"
        task.result_payload = {"detail": str(e)}
        db.commit()
    finally:
        db.close()

@router.post("/api/generate/timetables", status_code=202)
async def generate_timetables(background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = GenerationTask(status="PENDING")
    db.add(task)
    db.commit()
    db.refresh(task)
    
    background_tasks.add_task(run_solver_task, task.id)
    return {"task_id": task.id, "status": "PENDING"}

@router.get("/api/generate/status/{task_id}")
async def get_generation_status(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task.id, "status": task.status, "result": task.result_payload}
