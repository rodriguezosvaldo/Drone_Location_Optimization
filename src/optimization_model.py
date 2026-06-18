import gurobipy as gp
from visualizations.map_incidents_and_docks import create_map
from pathlib import Path
import webbrowser

_TIME_LIMIT_SECONDS = 300 # 300 seconds = 5 minutes time limit for the solver

def _configure_solver(model): 
    model.Params.TimeLimit = _TIME_LIMIT_SECONDS

def _precompute_coverage(docks, incidents):
    incident_to_docks = {} # List of docks that cover the incident
    for i in incidents:
        incident_to_docks[i] = i.covered_by(docks)
    dock_to_incidents = {} # List of incidents that are covered by the dock
    dock_distance_sum = {}
    for d in docks:
        covered_incidents, total_distance_to_covered_incidents = d.incidents_covered(incidents)
        dock_to_incidents[d] = covered_incidents
        dock_distance_sum[d] = total_distance_to_covered_incidents

    return incident_to_docks, dock_to_incidents, dock_distance_sum

def _coverage_weight(dock_distance_sum, dock_locations_quantity):
    max_tiebreak = max(dock_distance_sum.values(), default=0) * dock_locations_quantity
    return max_tiebreak + 1

def _build_base_model(docks, incidents, dock_locations_quantity, incident_to_docks, dock_to_incidents, max_dock_coverage_capacity):
    model = gp.Model("maximize_incidents_covered")
    _configure_solver(model)

    x = model.addVars(docks, vtype=gp.GRB.BINARY, name="x")
    y = model.addVars(incidents, vtype=gp.GRB.BINARY, name="y")

    for i in incidents:
        covering_docks = incident_to_docks[i]
        if covering_docks:
            model.addConstr(gp.quicksum(x[d] for d in covering_docks) >= y[i]) # Each incident must be covered by at least one dock
        else:
            model.addConstr(y[i] == 0) # If an incident is not covered by any dock, it must be set to 0

    for d in docks:
        coverable_incidents = dock_to_incidents[d]
        if coverable_incidents:
            model.addConstr(gp.quicksum(y[i] for i in coverable_incidents) <= max_dock_coverage_capacity) # The number of incidents covered by a dock must be less than or equal to the maximum number of incidents a dock can cover

    model.addConstr(gp.quicksum(x[d] for d in docks) <= dock_locations_quantity) # The number of docks must be less than or equal to the number of dock locations available
    model.addConstr(gp.quicksum(y[i] for i in incidents) <= dock_locations_quantity * max_dock_coverage_capacity) # Redundant constraint to ensure the number of incidents covered is less than or equal to the number of dock locations available multiplied by the maximum number of incidents a dock can cover
    return model, x, y

def maximize_incidents_covered(docks, incidents, dock_locations_quantity, max_dock_coverage_capacity):
    incident_to_docks, dock_to_incidents, dock_distance_sum = _precompute_coverage(docks, incidents)
    model, x, y = _build_base_model(docks, incidents, dock_locations_quantity, incident_to_docks, dock_to_incidents, max_dock_coverage_capacity)

    coverage_weight = _coverage_weight(dock_distance_sum, dock_locations_quantity)
    # Objective function: Maximize the number of incidents covered
    model.setObjective(
        coverage_weight * gp.quicksum(y[i] for i in incidents) - gp.quicksum(dock_distance_sum[d] * x[d] for d in docks), # Maximize the number of incidents covered minus the total travel distance to covered incidents
        gp.GRB.MAXIMIZE,
    )
    model.optimize()

    if model.Status not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT, gp.GRB.SUBOPTIMAL):
        print(f"Coverage optimization ended with status {model.Status}")
        return

    selected_docks = [d for d in docks if x[d].X > 0.5]
    covered_incidents = [i for i in incidents if y[i].X > 0.5]
    print(f"Selected docks amount: {len(selected_docks)}")
    print(f"Covered incidents amount: {len(covered_incidents)}")

    results = {
        "k": dock_locations_quantity,
        "incidents_covered": len(covered_incidents),
        "coverage_rate": len(covered_incidents) / len(incidents),
        "amount_selected_docks": len(selected_docks),
        "selected_docks": selected_docks,
        "covered_incidents": covered_incidents,
    }

    # Visualize map

    create_map(
        selected_docks,
        covered_incidents,
        "optimized_map",
        all_incidents=incidents,
        covered_incidents=covered_incidents,
    )
    map_file = Path(__file__).resolve().parent.parent / "output/optimized_map.html"
    if map_file.exists():
        webbrowser.open(map_file.resolve().as_uri())

    return results
    

    


