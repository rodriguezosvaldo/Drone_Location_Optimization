import gurobipy as gp
from src.docks_and_incidents import distance
from visualizations.map_incidents_and_docks import create_map
from pathlib import Path
import webbrowser
import math

_TIME_LIMIT_SECONDS = 300 # 300 seconds = 5 minutes time limit for the solver
PERCENTAGE_INCIDENTS_COVERED = 1 # 100% of incidents must be covered

def _precompute_coverage(docks, incidents):
    incident_to_docks = {} # List of docks that cover the incident
    for i in incidents:
        incident_to_docks[i] = i.covered_by(docks)
    dock_to_incidents = {} # List of incidents that are covered by the dock
    for d in docks:
        dock_to_incidents[d] = d.incidents_covered(incidents)[0]

    return incident_to_docks, dock_to_incidents

def maximize_incidents_covered(docks, incidents, dock_locations_quantity, specific_docks=None):
    incident_to_docks, dock_to_incidents = _precompute_coverage(docks, incidents)
    model = gp.Model("maximize_incidents_covered")
    model.Params.TimeLimit = _TIME_LIMIT_SECONDS

    # Constraints--------------------------------------------------------------------------------
    x = model.addVars(docks, vtype=gp.GRB.BINARY, name="x") # Binary variable indicating if a dock is open
    y = model.addVars(incidents, vtype=gp.GRB.BINARY, name="y") # Binary variable indicating if an incident is covered by a dock

    max_incidents = math.floor(PERCENTAGE_INCIDENTS_COVERED * len(incidents)) # floor to round down to the nearest integer and ceil to round up to the nearest integer
    model.addConstr(gp.quicksum(y[i] for i in incidents) <= max_incidents) # The number of incidents covered must be less than or equal to the maximum number of incidents that can be covered
    
    for i in incidents:
        covering_docks = incident_to_docks[i] # Docks that cover the incident
        if covering_docks:
            model.addConstr(gp.quicksum(x[d] for d in covering_docks) >= y[i]) # Each incident must be covered by at least one dock
        else:
            model.addConstr(y[i] == 0) # If an incident is not covered by any dock, it must be set to 0

    
    assignable_pairs = [(d, i) for i in incidents for d in incident_to_docks[i]] # Pairs of docks and incidents that are in range of each other
    pair_distance = {(d, i): distance(d, i) for d, i in assignable_pairs} # Distance between each dock and incident
    z = model.addVars(assignable_pairs, vtype=gp.GRB.BINARY, name="z") # Binary variable indicating if a dock covers an incident

    for i in incidents:
        model.addConstr(gp.quicksum(z[d, i] for d in incident_to_docks[i]) >= y[i]) # Each incident must be covered by at least one dock

    for d, i in assignable_pairs:
        model.addConstr(z[d, i] <= x[d]) # Each dock must be open to cover an incident
        model.addConstr(z[d, i] <= y[i]) # A dock can only be assigned to selected incidents(y[i] = 1)

    for d in docks:
        coverable_incidents = dock_to_incidents[d]
        if coverable_incidents:
            model.addConstr(
                gp.quicksum(z[d, i] for i in coverable_incidents)
                <= d.drone_coverage_capacity * x[d]
            ) # The number of incidents covered by a dock must be less than or equal to the maximum number of incidents a dock can cover
            model.addConstr(
                x[d] <= gp.quicksum(z[d, i] for i in coverable_incidents)
            ) # A dock can only be open if it covers at least one selected incident
        else:
            model.addConstr(x[d] == 0) # Docks that cannot cover any incident must remain closed
    model.addConstr(
        gp.quicksum(x[d] for d in docks) <= dock_locations_quantity) # The number of docks used must be less than or equal to the number of dock locations available
    # End Constraints--------------------------------------------------------------------------------
    

    # Objective functions: Maximize the number of incidents covered
    def max_coverage_first(model):
        # First priority: maximize the number of incidents covered
        model.setObjectiveN(
            gp.quicksum(y[i] for i in incidents),
            index=0, priority=2, abstol=1e-6, reltol=0,
            name="maximize_coverage"
        )
        # Second priority: minimize docks
        # model.setObjectiveN(
        #     -gp.quicksum(x[d] for d in docks),
        #     index=1, priority=1, abstol=1e-6, reltol=0,
        #     name="minimize_docks"
        # )

        # Third priority: minimize distance to assigned incidents
        model.setObjectiveN(
            -gp.quicksum(pair_distance[d, i] * z[d, i] for d, i in assignable_pairs),
            index=2, priority=0,
            name="minimize_distance"
        )

        model.ModelSense = gp.GRB.MAXIMIZE
        return model
    
    def specific_docks_first(model):
        remaining_docks = [d for d in docks if d not in specific_docks]
        remaining_pairs = [(d, i) for d, i in assignable_pairs if d in remaining_docks]
        specific_pairs = [(d, i) for d, i in assignable_pairs if d in specific_docks]
        # First priority: prioritize specific docks
        model.setObjectiveN(
            gp.quicksum(x[d] for d in specific_docks),
            index=0, priority=3, abstol=1e-6, reltol=0,
            name="specific_docks"
        )

        # Second priority: maximize the number of incidents covered
        model.setObjectiveN(
            gp.quicksum(y[i] for i in incidents),
            index=1, priority=2, abstol=1e-6, reltol=0,
            name="maximize_coverage"
        )

        # Third priority: minimize docks
        model.setObjectiveN(
            -gp.quicksum(x[d] for d in docks),
            index=2, priority=1, abstol=1e-6, reltol=0,
            name="minimize_docks"
        )

        # Fourth priority: minimize distance to assigned incidents
        model.setObjectiveN(
            -gp.quicksum(pair_distance[d, i] * z[d, i] for d, i in remaining_pairs) - gp.quicksum(pair_distance[d, i] * z[d, i] for d, i in specific_pairs),
            index=3, priority=0,
            name="minimize_distance"
        )
        model.ModelSense = gp.GRB.MAXIMIZE
        return model

    if specific_docks:
        model = specific_docks_first(model)
    else:
        model = max_coverage_first(model)

    model.optimize()
    if model.Status not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT, gp.GRB.SUBOPTIMAL):
        print(f"Coverage optimization ended with status {model.Status}")
        return

    selected_docks = [d for d in docks if x[d].X > 0.5]
    incidents_covered = [i for i in incidents if y[i].X > 0.5]
    dock_assignments = {
        d: [i for i in dock_to_incidents[d] if z[d, i].X > 0.5]
        for d in selected_docks
    }
    print(f"Selected docks amount: {len(selected_docks)}")
    print(f"Covered incidents amount: {len(incidents_covered)}")

    results = {
        "k": dock_locations_quantity,
        "amount_incidents_covered": len(incidents_covered),
        "coverage_rate": len(incidents_covered) / len(incidents),
        "amount_selected_docks": len(selected_docks),
        "selected_docks": selected_docks,
        "incidents_covered": incidents_covered,
        "dock_assignments": dock_assignments,
    }

    return results







def minimize_docks_used(docks, incidents):
    model = gp.Model("minimize_docks_used")
    model.Params.TimeLimit = _TIME_LIMIT_SECONDS
    incident_to_docks, dock_to_incidents = _precompute_coverage(docks, incidents)
    assignable_pairs = [(d, i) for i in incidents for d in incident_to_docks[i]]

    x = model.addVars(docks, vtype=gp.GRB.BINARY, name="x") # Binary variable indicating if a dock is open
    y = model.addVars(assignable_pairs, vtype=gp.GRB.BINARY, name="y") # Binary variable indicating if an incident is covered by a dock

    for i in incidents:
        model.addConstr(gp.quicksum(y[d, i] for d in incident_to_docks[i]) >= 1) # Each incident must be covered by at least one dock

    for d in docks:
        coverable_incidents = dock_to_incidents[d]
        if coverable_incidents:
            model.addConstr(
                gp.quicksum(y[d, i] for i in coverable_incidents)
                <= d.drone_coverage_capacity * x[d]
            ) # The number of incidents covered by a dock must be less than or equal to the maximum number of incidents a dock can cover
    
    model.setObjective(gp.quicksum(x[d] for d in docks), gp.GRB.MINIMIZE) # Minimize the number of docks used
    model.optimize()
    if model.Status not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT, gp.GRB.SUBOPTIMAL):
        print(f"Dock minimization ended with status {model.Status}")
        return

    selected_docks = [d for d in docks if x[d].X > 0.5]
    covered_incidents = [i for i in incidents if any(y[d, i].X > 0.5 for d in incident_to_docks[i])]
    dock_assignments = {
        d: [i for i in dock_to_incidents[d] if y[d, i].X > 0.5]
        for d in selected_docks
    }
    print(f"Selected docks amount: {len(selected_docks)}")
    print(f"Covered incidents amount: {len(covered_incidents)}")

    # Visualize map

    create_map(
        selected_docks,
        incidents,
        "minimized_docks_used_map",
        covered_incidents,
        dock_assignments,
    )
    map_file = Path(__file__).resolve().parent.parent.parent / "output" / "minimized_docks_used_map.html"
    if map_file.exists():
        webbrowser.open(map_file.resolve().as_uri())