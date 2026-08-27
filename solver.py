from ortools.sat.python import cp_model

def build_timetable_model(workload_data, classes, rooms):
    model = cp_model.CpModel()
    
    num_days = 5
    num_periods = 6 # Strict 6-period day (no break modeled)
    
    faculties = list(set([item['faculty_id'] for item in workload_data]))
    
    # Process rooms
    venues = [r.venue_name for r in rooms]
    venue_types = {r.venue_name: r.type for r in rooms}
    
    schedule = {}
    
    for item in workload_data:
        f = item['faculty_id']
        s = item['section']
        sub = item['subject']
        for d in range(num_days):
            for p in range(num_periods):
                var_name = f"schedule_f{f}_s{s}_sub{sub}_d{d}_p{p}"
                schedule[(f, s, sub, d, p)] = model.NewBoolVar(var_name)
                
    # Create parallel venue matrix
    venue_schedule = {}
    for s in classes:
        for d in range(num_days):
            for p in range(num_periods):
                for v in venues:
                    venue_schedule[(s, d, p, v)] = model.NewBoolVar(f"venue_{s}_d{d}_p{p}_v{v}")
                    
    # Link schedule to venue_schedule
    for d in range(num_days):
        for p in range(num_periods):
            for s in classes:
                is_busy = []
                for k, var in schedule.items():
                    if k[1] == s and k[3] == d and k[4] == p:
                        is_busy.append(var)
                        
                section_busy_var = model.NewBoolVar(f"sec_busy_{s}_d{d}_p{p}")
                model.Add(sum(is_busy) == 1).OnlyEnforceIf(section_busy_var)
                model.Add(sum(is_busy) == 0).OnlyEnforceIf(section_busy_var.Not())
                
                venue_vars = [venue_schedule[(s, d, p, v)] for v in venues]
                model.Add(sum(venue_vars) == 1).OnlyEnforceIf(section_busy_var)
                model.Add(sum(venue_vars) == 0).OnlyEnforceIf(section_busy_var.Not())
                
                for k, var in schedule.items():
                    if k[1] == s and k[3] == d and k[4] == p:
                        f, _, sub = k[:3]
                        req = next((item for item in workload_data if item['section'] == s and item['subject'] == sub), None)
                        if not req: continue
                        
                        req_venue = req.get('required_venue')
                        if req_venue and req_venue in venues:
                            model.AddImplication(var, venue_schedule[(s, d, p, req_venue)])
                        
                        sub_type = req.get('type', '').upper()
                        if 'LAB' in sub_type:
                            valid_venues = [v for v in venues if venue_types.get(v, '').upper() == 'LAB']
                            if valid_venues:
                                model.Add(sum(venue_schedule[(s, d, p, v)] for v in valid_venues) == 1).OnlyEnforceIf(var)
                        elif 'THEORY' in sub_type:
                            valid_venues = [v for v in venues if venue_types.get(v, '').upper() == 'THEORY']
                            if valid_venues:
                                model.Add(sum(venue_schedule[(s, d, p, v)] for v in valid_venues) == 1).OnlyEnforceIf(var)
                                
    # Anti-overlap for venues
    for d in range(num_days):
        for p in range(num_periods):
            for v in venues:
                model.Add(sum(venue_schedule[(s, d, p, v)] for s in classes) <= 1)
                    
    # 1. No Faculty Overlap
    for f in faculties:
        for d in range(num_days):
            for p in range(num_periods):
                vars_for_faculty = [schedule[k] for k in schedule if k[0] == f and k[3] == d and k[4] == p]
                if vars_for_faculty:
                    model.AddAtMostOne(vars_for_faculty)
                    
    # 2. No Section Overlap
    for s in classes:
        for d in range(num_days):
            for p in range(num_periods):
                vars_for_section = [schedule[k] for k in schedule if k[1] == s and k[3] == d and k[4] == p]
                if vars_for_section:
                    model.AddAtMostOne(vars_for_section)
                    
    # 3. Workload Fulfillment
    for item in workload_data:
        f = item['faculty_id']
        s = item['section']
        sub = item['subject']
        hours = item['hours']
        vars_for_assignment = [schedule[k] for k in schedule if k[0] == f and k[1] == s and k[2] == sub]
        model.Add(sum(vars_for_assignment) == hours)
        
    # 4. Asymmetry Rule (Faculty >= 1 free slot)
    for f in faculties:
        vars_for_faculty = [schedule[k] for k in schedule if k[0] == f]
        model.Add(sum(vars_for_faculty) <= (num_days * num_periods) - 1)
        
    # Penalty Array for Soft Constraints
    penalty_vars = []
    
    # 5. Type-Specific Constraints
    for item in workload_data:
        s = item['section']
        sub = item['subject']
        f = item['faculty_id']
        sub_type = str(item.get('type', 'THEORY')).upper()
        hours = item['hours']
        
        # THEORY CONSTRAINT
        if sub_type == 'THEORY':
            for d in range(num_days):
                vars_for_daily_sub = [schedule[k] for k in schedule if k[1] == s and k[2] == sub and k[3] == d]
                if vars_for_daily_sub:
                    model.Add(sum(vars_for_daily_sub) <= 2) # Max 2 per day
                    
                # Soft Penalty for Period 0 and Period 5 (Last)
                for p in [0, num_periods - 1]:
                    if (f, s, sub, d, p) in schedule:
                        penalty_vars.append(schedule[(f, s, sub, d, p)])
                        
        # LAB CONSTRAINT (Max 2 consecutive)
        elif sub_type == 'LAB':
            # Rolling window constraint: No more than 2 periods in any 3 consecutive periods for this specific lab subject
            for d in range(num_days):
                for p in range(num_periods - 2):
                    v1 = schedule.get((f, s, sub, d, p))
                    v2 = schedule.get((f, s, sub, d, p+1))
                    v3 = schedule.get((f, s, sub, d, p+2))
                    if v1 is not None and v2 is not None and v3 is not None:
                        model.Add(v1 + v2 + v3 <= 2)
                        
            # Force chunks of 2-hours
            chunks = hours // 2
            if chunks > 0:
                start_vars = []
                for d in range(num_days):
                    for p in range(num_periods - 1):
                        start_var = model.NewBoolVar(f"start_lab_{f}_{s}_{sub}_d{d}_p{p}")
                        start_vars.append(start_var)
                        model.AddImplication(start_var, schedule[(f, s, sub, d, p)])
                        model.AddImplication(start_var, schedule[(f, s, sub, d, p + 1)])
                        
                        # Isolate the block (separated by breaks or other subjects)
                        if p + 2 < num_periods:
                            model.AddImplication(start_var, schedule[(f, s, sub, d, p + 2)].Not())
                        if p - 1 >= 0:
                            model.AddImplication(start_var, schedule[(f, s, sub, d, p - 1)].Not())
                            
                model.Add(sum(start_vars) == chunks)

    # 6. Elective/Language Synchronization
    sync_subjects = {}
    for item in workload_data:
        sub_type = str(item.get('type', 'THEORY')).upper()
        if sub_type in ['ELECTIVE', 'LANGUAGE']:
            sub = item['subject']
            if sub not in sync_subjects:
                sync_subjects[sub] = []
            sync_subjects[sub].append(item)
            
    for sub, items in sync_subjects.items():
        if len(items) > 1:
            first_item = items[0]
            f1 = first_item['faculty_id']
            s1 = first_item['section']
            for other_item in items[1:]:
                f2 = other_item['faculty_id']
                s2 = other_item['section']
                for d in range(num_days):
                    for p in range(num_periods):
                        v1 = schedule.get((f1, s1, sub, d, p))
                        v2 = schedule.get((f2, s2, sub, d, p))
                        if v1 is not None and v2 is not None:
                            model.Add(v1 == v2)
                            
    # Objective: Minimize penalties
    if penalty_vars:
        model.Minimize(sum(penalty_vars))
        
    return model, schedule, venue_schedule, venues

def diagnostic_pre_check(workload_data, classes):
    print("--- STRICT DIAGNOSTIC PRE-CHECK ---")
    
    # 1. Workload Audit: Faculty and Sections
    faculty_hours = {}
    section_hours = {}
    for item in workload_data:
        f = item['faculty_id']
        s = item['section']
        h = item['hours']
        faculty_hours[f] = faculty_hours.get(f, 0) + h
        section_hours[s] = section_hours.get(s, 0) + h
        
    for f, h in faculty_hours.items():
        print(f"Faculty [{f}] Total Hours: {h}")
        if h > 29:
            print(f"  [CRITICAL WARNING] Faculty {f} exceeds 29 hours (Assigned: {h}). Asymmetry Rule VIOLATED!")
            
    for s, h in section_hours.items():
        print(f"Section [{s}] Total Hours: {h}")
        if h > 30:
            print(f"  [CRITICAL WARNING] Section {s} exceeds 30 hours (Assigned: {h}). 5x6 Matrix VIOLATED!")
        elif h < 30:
            print(f"  [WARNING] Section {s} is under 30 hours (Assigned: {h}). Matrix will have forced free slots!")
            
    # 2. Lab Block Audit (Removed since >2 hours are successfully chunked via rolling window)
                
    # 3. Elective Parity Check
    sync_subjects = {}
    for item in workload_data:
        sub_type = str(item.get('type', 'THEORY')).upper()
        if sub_type in ['ELECTIVE', 'LANGUAGE']:
            sub = item['subject']
            if sub not in sync_subjects:
                sync_subjects[sub] = []
            sync_subjects[sub].append(item)
            
    for sub, items in sync_subjects.items():
        if len(items) > 1:
            hours_set = set([i['hours'] for i in items])
            if len(hours_set) > 1:
                print(f"  [CRITICAL WARNING] Elective Parity Mismatch for '{sub}' across sections! Hours found: {hours_set}")
                
    print("--- PRE-CHECK COMPLETE ---")

def solve_timetable(workload_data, classes, rooms):
    diagnostic_pre_check(workload_data, classes)
    
    model, schedule, venue_schedule, venues = build_timetable_model(workload_data, classes, rooms)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0 # Bounded search time for batch parallel grid
    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    
    parsed_schedule = []
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for key, var in schedule.items():
            if solver.BooleanValue(var):
                f, s, sub, d, p = key
                
                # Determine which venue was assigned for this block
                assigned_venue = "Unknown"
                for v in venues:
                    if solver.BooleanValue(venue_schedule[(s, d, p, v)]):
                        assigned_venue = v
                        break
                        
                parsed_schedule.append({
                    "faculty_id": f,
                    "section": s,
                    "subject": sub,
                    "day": d,
                    "period": p,
                    "venue": assigned_venue
                })
                
    return {
        "status": status_name,
        "blocks": parsed_schedule
    }
