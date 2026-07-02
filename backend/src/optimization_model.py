import math

import gurobipy as gp

from src.docks_and_incidents import distance

_TIME_LIMIT_SECONDS = 300


class MaximizeIncidentsCovered:
    """Maximize incident coverage subject to a dock budget and optional priority docks."""

    def __init__(
        self,
        docks,
        incidents,
        budget,
        priority_docks=None,
        percentage_incidents_to_cover=100,
    ):
        self.docks = docks
        self.incidents = incidents
        self.budget = budget
        self.priority_docks = priority_docks or []
        self.percentage_incidents_to_cover = percentage_incidents_to_cover

    def _precompute_coverage(self):
        incident_to_docks = {}
        for incident in self.incidents:
            incident_to_docks[incident] = incident.covered_by(self.docks)

        dock_to_incidents = {}
        for dock in self.docks:
            dock_to_incidents[dock] = dock.incidents_covered(self.incidents)[0]

        return incident_to_docks, dock_to_incidents

    def _build_model(self, incident_to_docks, dock_to_incidents):
        docks = self.docks
        incidents = self.incidents

        model = gp.Model("maximize_incidents_covered")
        model.Params.TimeLimit = _TIME_LIMIT_SECONDS

        x = model.addVars(docks, vtype=gp.GRB.BINARY, name="x")
        y = model.addVars(incidents, vtype=gp.GRB.BINARY, name="y")

        max_incidents = math.floor(
            (self.percentage_incidents_to_cover / 100) * len(incidents)
        )
        model.addConstr(gp.quicksum(y[i] for i in incidents) <= max_incidents)

        for incident in incidents:
            covering_docks = incident_to_docks[incident]
            if covering_docks:
                model.addConstr(gp.quicksum(x[d] for d in covering_docks) >= y[incident])
            else:
                model.addConstr(y[incident] == 0)

        assignable_pairs = [
            (dock, incident)
            for incident in incidents
            for dock in incident_to_docks[incident]
        ]
        pair_distance = {(dock, incident): distance(dock, incident) for dock, incident in assignable_pairs}
        z = model.addVars(assignable_pairs, vtype=gp.GRB.BINARY, name="z")

        for incident in incidents:
            model.addConstr(
                gp.quicksum(z[dock, incident] for dock in incident_to_docks[incident]) >= y[incident]
            )

        for dock, incident in assignable_pairs:
            model.addConstr(z[dock, incident] <= x[dock])
            model.addConstr(z[dock, incident] <= y[incident])

        for dock in docks:
            coverable_incidents = dock_to_incidents[dock]
            if coverable_incidents:
                model.addConstr(
                    gp.quicksum(z[dock, incident] for incident in coverable_incidents)
                    <= dock.drone_coverage_capacity * x[dock]
                )
                model.addConstr(
                    x[dock] <= gp.quicksum(z[dock, incident] for incident in coverable_incidents)
                )
            else:
                model.addConstr(x[dock] == 0)

        model.addConstr(gp.quicksum(x[dock] for dock in docks) <= self.budget)

        return model, x, y, z, assignable_pairs, pair_distance

    def _max_coverage_first(self, model, x, y, z, assignable_pairs, pair_distance):
        docks = self.docks
        incidents = self.incidents

        model.setObjectiveN(
            gp.quicksum(y[i] for i in incidents),
            index=0,
            priority=2,
            abstol=1e-6,
            reltol=0,
            name="maximize_coverage",
        )
        model.setObjectiveN(
            -gp.quicksum(x[d] for d in docks),
            index=1,
            priority=1,
            abstol=1e-6,
            reltol=0,
            name="minimize_docks",
        )
        model.setObjectiveN(
            -gp.quicksum(pair_distance[d, i] * z[d, i] for d, i in assignable_pairs),
            index=2,
            priority=0,
            name="minimize_distance",
        )
        model.ModelSense = gp.GRB.MAXIMIZE

    def _specific_docks_first(self, model, x, y, z, assignable_pairs, pair_distance):
        docks = self.docks
        incidents = self.incidents
        priority_docks = self.priority_docks

        remaining_docks = [dock for dock in docks if dock not in priority_docks]
        remaining_pairs = [(d, i) for d, i in assignable_pairs if d in remaining_docks]
        specific_pairs = [(d, i) for d, i in assignable_pairs if d in priority_docks]

        model.setObjectiveN(
            gp.quicksum(x[d] for d in priority_docks),
            index=0,
            priority=3,
            abstol=1e-6,
            reltol=0,
            name="specific_docks",
        )
        model.setObjectiveN(
            gp.quicksum(y[i] for i in incidents),
            index=1,
            priority=2,
            abstol=1e-6,
            reltol=0,
            name="maximize_coverage",
        )
        model.setObjectiveN(
            -gp.quicksum(x[d] for d in docks),
            index=2,
            priority=1,
            abstol=1e-6,
            reltol=0,
            name="minimize_docks",
        )
        model.setObjectiveN(
            -gp.quicksum(pair_distance[d, i] * z[d, i] for d, i in remaining_pairs)
            - gp.quicksum(pair_distance[d, i] * z[d, i] for d, i in specific_pairs),
            index=3,
            priority=0,
            name="minimize_distance",
        )
        model.ModelSense = gp.GRB.MAXIMIZE

    def _set_objectives(self, model, x, y, z, assignable_pairs, pair_distance):
        if self.priority_docks:
            self._specific_docks_first(model, x, y, z, assignable_pairs, pair_distance)
        else:
            self._max_coverage_first(model, x, y, z, assignable_pairs, pair_distance)

    def _extract_results(self, model, x, y, z, dock_to_incidents):
        if model.Status not in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT, gp.GRB.SUBOPTIMAL):
            print(f"Coverage optimization ended with status {model.Status}")
            return None

        selected_docks = [dock for dock in self.docks if x[dock].X > 0.5]
        incidents_covered = [incident for incident in self.incidents if y[incident].X > 0.5]
        dock_assignments = {
            dock: [incident for incident in dock_to_incidents[dock] if z[dock, incident].X > 0.5]
            for dock in selected_docks
        }

        return {
            "k": self.budget,
            "amount_incidents_covered": len(incidents_covered),
            "coverage_rate": len(incidents_covered) / len(self.incidents) if self.incidents else 0,
            "amount_selected_docks": len(selected_docks),
            "selected_docks": selected_docks,
            "incidents_covered": incidents_covered,
            "dock_assignments": dock_assignments,
            "response_time": self.docks[0].response_time if self.docks else None,
        }

    def run(self):
        incident_to_docks, dock_to_incidents = self._precompute_coverage()
        model, x, y, z, assignable_pairs, pair_distance = self._build_model(
            incident_to_docks,
            dock_to_incidents,
        )
        self._set_objectives(model, x, y, z, assignable_pairs, pair_distance)
        model.optimize()
        return self._extract_results(model, x, y, z, dock_to_incidents)
