import math
import time

import pulp

from src.docks_and_incidents import distance

_TIME_LIMIT_SECONDS = 300
_ACCEPTABLE_STATUSES = {
    pulp.LpStatusOptimal,
    pulp.LpStatusNotSolved,  # time limit / early stop can still yield a feasible solution
}


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

        model = pulp.LpProblem("maximize_incidents_covered", pulp.LpMaximize)

        x = {
            dock: pulp.LpVariable(f"x_{i}", cat=pulp.LpBinary)
            for i, dock in enumerate(docks)
        }
        y = {
            incident: pulp.LpVariable(f"y_{i}", cat=pulp.LpBinary)
            for i, incident in enumerate(incidents)
        }

        max_incidents = math.floor(
            (self.percentage_incidents_to_cover / 100) * len(incidents)
        )
        model += pulp.lpSum(y[i] for i in incidents) <= max_incidents

        for incident in incidents:
            covering_docks = incident_to_docks[incident]
            if covering_docks:
                model += pulp.lpSum(x[d] for d in covering_docks) >= y[incident]
            else:
                model += y[incident] == 0

        assignable_pairs = [
            (dock, incident)
            for incident in incidents
            for dock in incident_to_docks[incident]
        ]
        pair_distance = {
            (dock, incident): distance(dock, incident) for dock, incident in assignable_pairs
        }
        z = {
            (dock, incident): pulp.LpVariable(f"z_{i}", cat=pulp.LpBinary)
            for i, (dock, incident) in enumerate(assignable_pairs)
        }

        for incident in incidents:
            model += (
                pulp.lpSum(z[dock, incident] for dock in incident_to_docks[incident])
                >= y[incident]
            )

        for dock, incident in assignable_pairs:
            model += z[dock, incident] <= x[dock]
            model += z[dock, incident] <= y[incident]

        for dock in docks:
            coverable_incidents = dock_to_incidents[dock]
            if coverable_incidents:
                model += (
                    pulp.lpSum(z[dock, incident] for incident in coverable_incidents)
                    <= dock.drone_coverage_capacity * x[dock]
                )
                model += x[dock] <= pulp.lpSum(
                    z[dock, incident] for incident in coverable_incidents
                )
            else:
                model += x[dock] == 0

        model += pulp.lpSum(x[dock] for dock in docks) <= self.budget

        return model, x, y, z, assignable_pairs, pair_distance

    def _max_coverage_objectives(self, x, y, z, assignable_pairs, pair_distance):
        """Highest priority first: coverage, then fewer docks, then shorter distance."""
        return [
            (pulp.lpSum(y[i] for i in self.incidents), pulp.LpMaximize, 1e-6, "maximize_coverage"),
            (pulp.lpSum(x[d] for d in self.docks), pulp.LpMinimize, 1e-6, "minimize_docks"),
            (
                pulp.lpSum(pair_distance[d, i] * z[d, i] for d, i in assignable_pairs),
                pulp.LpMinimize,
                1e-6,
                "minimize_distance",
            ),
        ]

    def _specific_docks_objectives(self, model, x, y, z, assignable_pairs, pair_distance):
        docks = self.docks
        incidents = self.incidents
        priority_docks = self.priority_docks

        remaining_pairs = [(d, i) for d, i in assignable_pairs if d not in priority_docks]
        specific_pairs = [(d, i) for d, i in assignable_pairs if d in priority_docks]
        priority_pairs_by_incident = {incident: [] for incident in incidents}
        for dock, incident in specific_pairs:
            priority_pairs_by_incident[incident].append((dock, incident))

        w = {
            incident: pulp.LpVariable(f"w_{i}", cat=pulp.LpBinary)
            for i, incident in enumerate(incidents)
        }
        for incident in incidents:
            priority_pairs = priority_pairs_by_incident[incident]
            if priority_pairs:
                model += w[incident] <= pulp.lpSum(
                    z[dock, inc] for dock, inc in priority_pairs
                )
            else:
                model += w[incident] == 0
            model += w[incident] <= y[incident]

        return [
            (
                pulp.lpSum(w[i] for i in incidents),
                pulp.LpMaximize,
                1e-6,
                "priority_incident_coverage",
            ),
            (pulp.lpSum(y[i] for i in incidents), pulp.LpMaximize, 1e-6, "maximize_coverage"),
            (pulp.lpSum(x[d] for d in docks), pulp.LpMinimize, 1e-6, "minimize_docks"),
            (
                pulp.lpSum(pair_distance[d, i] * z[d, i] for d, i in remaining_pairs)
                + pulp.lpSum(pair_distance[d, i] * z[d, i] for d, i in specific_pairs),
                pulp.LpMinimize,
                1e-6,
                "minimize_distance",
            ),
        ]

    def _set_objectives(self, model, x, y, z, assignable_pairs, pair_distance):
        if self.priority_docks:
            return self._specific_docks_objectives(
                model, x, y, z, assignable_pairs, pair_distance
            )
        return self._max_coverage_objectives(x, y, z, assignable_pairs, pair_distance)

    def _solve_lexicographic(self, model, objectives):
        """Solve hierarchical objectives sequentially (open-source equivalent of setObjectiveN)."""
        deadline = time.time() + _TIME_LIMIT_SECONDS
        last_status = None

        for stage, (expr, sense, abstol, name) in enumerate(objectives):
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            model.sense = sense
            model.objective = expr

            status = model.solve(
                pulp.HiGHS(msg=False, timeLimit=max(remaining, 1.0))
            )
            last_status = status

            if pulp.LpStatus[status] == "Infeasible":
                print(f"Coverage optimization ended with status {pulp.LpStatus[status]}")
                return None

            obj_value = pulp.value(expr)
            if obj_value is None:
                print(f"Coverage optimization ended with status {pulp.LpStatus[status]}")
                return None

            # Freeze this priority level before optimizing lower-priority goals.
            if stage < len(objectives) - 1:
                if sense == pulp.LpMaximize:
                    model += expr >= obj_value - abstol, f"_fix_{name}"
                else:
                    model += expr <= obj_value + abstol, f"_fix_{name}"

        return last_status

    def _extract_results(self, status, x, y, z, dock_to_incidents):
        if status is None or status not in _ACCEPTABLE_STATUSES:
            # Still accept a feasible incumbent if variable values are present.
            sample = next(iter(x.values()), None)
            if sample is None or pulp.value(sample) is None:
                print(f"Coverage optimization ended with status {pulp.LpStatus.get(status, status)}")
                return None

        selected_docks = [dock for dock in self.docks if (pulp.value(x[dock]) or 0) > 0.5]
        incidents_covered = [
            incident for incident in self.incidents if (pulp.value(y[incident]) or 0) > 0.5
        ]
        dock_assignments = {
            dock: [
                incident
                for incident in dock_to_incidents[dock]
                if (pulp.value(z[dock, incident]) or 0) > 0.5
            ]
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
            "drone_speed": self.docks[0].drone_speed if self.docks else None,
            "response_time": self.docks[0].response_time if self.docks else None,
        }

    def run(self):
        incident_to_docks, dock_to_incidents = self._precompute_coverage()
        model, x, y, z, assignable_pairs, pair_distance = self._build_model(
            incident_to_docks,
            dock_to_incidents,
        )
        objectives = self._set_objectives(model, x, y, z, assignable_pairs, pair_distance)
        status = self._solve_lexicographic(model, objectives)
        return self._extract_results(status, x, y, z, dock_to_incidents)
