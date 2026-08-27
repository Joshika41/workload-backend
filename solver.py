from ortools.sat.python import cp_model

def solve_timetable(workload_data, classes, rooms=None):
    model = cp_model.CpModel()
    num_days = 5
    num_periods = 6
    
    faculties = list(set([item['faculty_id'] for item in workload_data]))
    schedule = {}
    
    for item in workload_data:
        f = item['faculty_id']
        s = item['section']
        sub = item['subject']
        for d in range(num_days):
            for p in range(num_periods):
                # Boolean variable: 1 if this faculty teaches this subject to this section on day d period p
                var_name = f's_{f}_{s}_{sub}_d{d}_p{p}'
                schedule[(f, s, sub, d, p)] = model.NewBoolVar(var_name)
                
    # CONSTRAINT 1: Faculty cannot be double booked
    for f in faculties:
        for d in range(num_days):
            for p in range(num_periods):
                model.Add(sum(schedule[(f, item['section'], item['subject'], d, p)] 
                              for item in workload_data if item['faculty_id'] == f) <= 1)

    # CONSTRAINT 2: Classes must be fully occupied (no free slots)
    for s in classes:
        for d in range(num_days):
            for p in range(num_periods):
                model.Add(sum(schedule[(item['faculty_id'], s, item['subject'], d, p)] 
                              for item in workload_data if item['section'] == s) == 1)

    # CONSTRAINT 3: Exact hours requirement
    for item in workload_data:
        f = item['faculty_id']
        s = item['section']
        sub = item['subject']
        hours = item['hours']
        model.Add(sum(schedule[(f, s, sub, d, p)] for d in range(num_days) for p in range(num_periods)) == hours)

    # CONSTRAINT 4: Same subject not more than 2 times a day (theory & lab)
    for item in workload_data:
        f = item['faculty_id']
        s = item['section']
        sub = item['subject']
        for d in range(num_days):
            model.Add(sum(schedule[(f, s, sub, d, p)] for p in range(num_periods)) <= 2)

    # CONSTRAINT 5: Lab sessions must be 2 consecutive hours (block constraint)
    for item in workload_data:
        if item.get('type', 'THEORY').upper() == 'LAB' and item['hours'] >= 2:
            f = item['faculty_id']
            s = item['section']
            sub = item['subject']
            # For each day, if a lab is scheduled, it must be consecutive. 
            # We enforce that the sum of blocks equals the number of start blocks * 2.
            # A start block is when p is 1 and p-1 is 0.
            for d in range(num_days):
                day_vars = [schedule[(f, s, sub, d, p)] for p in range(num_periods)]
                # Add contiguous logic:
                # Easiest way in CP-SAT: if p=0 is 1 and p=1 is 0, it's not a block of 2.
                # Actually, simpler constraint: total daily hours must be either 0 or 2.
                daily_sum = sum(day_vars)
                # It can be 0 or 2
                b0 = model.NewBoolVar(f'lab_0_{f}_{s}_{sub}_{d}')
                b2 = model.NewBoolVar(f'lab_2_{f}_{s}_{sub}_{d}')
                model.Add(daily_sum == 0).OnlyEnforceIf(b0)
                model.Add(daily_sum == 2).OnlyEnforceIf(b2)
                model.AddBoolOr([b0, b2])
                
                # If it's 2, they must be adjacent: sum(day_vars[i] * day_vars[i+1]) == 1
                # But multiplication of variables is not allowed directly. We use a boolean for adjacency.
                adjacencies = []
                for p in range(num_periods - 1):
                    adj = model.NewBoolVar(f'adj_{f}_{s}_{sub}_{d}_{p}')
                    # adj == (day_vars[p] AND day_vars[p+1])
                    model.AddBoolAnd([day_vars[p], day_vars[p+1]]).OnlyEnforceIf(adj)
                    model.AddBoolOr([day_vars[p].Not(), day_vars[p+1].Not()]).OnlyEnforceIf(adj.Not())
                    adjacencies.append(adj)
                
                model.Add(sum(adjacencies) == 1).OnlyEnforceIf(b2)
                model.Add(sum(adjacencies) == 0).OnlyEnforceIf(b0)

    # CONSTRAINT 6: Same subject should not be first or last hour EVERY DAY throughout the week.
    # To prevent a subject from dominating the first/last slots.
    for item in workload_data:
        f = item['faculty_id']
        s = item['section']
        sub = item['subject']
        # Max 2 times at period 0 per week
        model.Add(sum(schedule[(f, s, sub, d, 0)] for d in range(num_days)) <= 2)
        # Max 2 times at period 5 per week
        model.Add(sum(schedule[(f, s, sub, d, num_periods-1)] for d in range(num_days)) <= 2)

    # OPTIMIZATION: Try to give faculties at least one free slot in the week.
    # We already have max hours constraints handled by validation, but CP-SAT can just solve it.
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    status = solver.Solve(model)
    
    blocks = []
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for item in workload_data:
            f = item['faculty_id']
            s = item['section']
            sub = item['subject']
            for d in range(num_days):
                for p in range(num_periods):
                    if solver.Value(schedule[(f, s, sub, d, p)]):
                        blocks.append({
                            'faculty_id': f, 
                            'section': s, 
                            'subject': sub, 
                            'day': d, 
                            'period': p
                        })
                        
    return {'status': solver.StatusName(status), 'blocks': blocks}
