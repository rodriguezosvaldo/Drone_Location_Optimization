from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.config import OUTPUT_DIR
from app.services.session import session
from src.docks_and_incidents import (
    clone_docks,
    create_docks_and_incidents,
    filter_priority_area,
    peak_day_incidents,
)
from src.optimization_model import MaximizeIncidentsCovered
from visualizations.charts_optimization_results import (
    chart_dock_efficiency_vs_docks,
    chart_incidents_covered_vs_k,
    chart_incidents_covered_vs_percentage,
)
from visualizations.map_incidents_and_docks import create_map


def _ensure_backend_cwd() -> None:
    backend_root = Path(__file__).resolve().parent.parent.parent
    os.chdir(backend_root)


def _priority_dock_names() -> list[str]:
    return list(session.priority_dock_names or [])


def _priority_docks(docks: list[Any]) -> list[Any]:
    if not docks or not session.priority_dock_names:
        return []
    return [dock for dock in docks if dock.name in session.priority_dock_names]


def _serialize_result(result: dict, *, target_percentage: float | None = None) -> dict:
    total = result.get("amount_incidents_covered", 0)
    coverage_rate = result.get("coverage_rate", 0)
    payload = {
        "k": result["k"],
        "amount_incidents_covered": total,
        "coverage_rate": round(coverage_rate * 100, 2),
        "amount_selected_docks": result["amount_selected_docks"],
        "selected_docks": [d.name for d in result["selected_docks"]],
    }
    if target_percentage is not None:
        payload["target_percentage"] = target_percentage
    if result.get("drone_speed") is not None:
        payload["drone_speed_mph"] = round(result["drone_speed"], 2)
    if result.get("response_time") is not None:
        payload["response_time_minutes"] = round(result["response_time"] * 60, 2)
    return payload


def build_percentage_range_values(start: float, end: float, step: float) -> list[float]:
    values: list[float] = []
    current = start
    while current <= end + 1e-9:
        values.append(round(current, 6))
        current += step
    return values


def _relative_output_path(path: Path) -> str:
    try:
        return str(path.relative_to(OUTPUT_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _map_kwargs() -> dict[str, float]:
    if session.area_bounds is None:
        return {}
    return dict(session.area_bounds)


def _require_loaded_data() -> None:
    if (
        not session.loaded
        or session.docks is None
        or session.all_incidents is None
        or not session.priority_dock_names
    ):
        raise ValueError("Upload incidents, docks, and priority docks files before continuing.")


def _resolve_area_context(area: str, peak_day_only: bool) -> tuple[list[Any], list[Any], dict[str, float] | None]:
    _require_loaded_data()

    if area == "full":
        docks = session.docks
        incidents = session.incidents_in_one_day if peak_day_only else session.all_incidents
        bounds = None
    elif area == "specific":
        if not session.priority_dock_names:
            raise ValueError("Upload a priority docks file before using the priority area.")
        if session.priority_area_docks is None or session.priority_area_all_incidents is None:
            docks, area_incidents, bounds = filter_priority_area(
                session.docks,
                session.all_incidents,
                session.priority_dock_names,
            )
            session.priority_area_docks = docks
            session.priority_area_all_incidents = area_incidents
            session.priority_area_peak_incidents = peak_day_incidents(area_incidents)
            session.priority_area_bounds = bounds
        docks = session.priority_area_docks
        bounds = session.priority_area_bounds
        incidents = (
            session.priority_area_peak_incidents
            if peak_day_only
            else session.priority_area_all_incidents
        )
    else:
        raise ValueError('area must be "full" or "specific".')

    if not incidents:
        raise ValueError("No incidents available for the selected area and day filter.")

    return docks, incidents, bounds


def _precompute_priority_area() -> None:
    if not session.docks or not session.all_incidents or not session.priority_dock_names:
        session.priority_area_docks = None
        session.priority_area_all_incidents = None
        session.priority_area_peak_incidents = None
        session.priority_area_bounds = None
        session.priority_area_all_incidents_count = 0
        session.priority_area_peak_incidents_count = 0
        return

    docks, area_incidents, bounds = filter_priority_area(
        session.docks,
        session.all_incidents,
        session.priority_dock_names,
    )
    peak_incidents = peak_day_incidents(area_incidents)

    session.priority_area_docks = docks
    session.priority_area_all_incidents = area_incidents
    session.priority_area_peak_incidents = peak_incidents
    session.priority_area_bounds = bounds
    session.priority_area_all_incidents_count = len(area_incidents)
    session.priority_area_peak_incidents_count = len(peak_incidents)


def load_priority_docks(priority_path: Path) -> dict[str, Any]:
    _ensure_backend_cwd()
    if not priority_path.exists():
        raise FileNotFoundError(f"Priority docks file not found: {priority_path}")

    import pandas as pd

    data = pd.read_excel(priority_path)
    if "name" not in data.columns:
        raise ValueError('Priority docks file must include a "name" column.')

    names = [str(name).strip() for name in data["name"].dropna().tolist() if str(name).strip()]
    if not names:
        raise ValueError("Priority docks file does not contain any dock names.")

    session.priority_dock_names = names
    if session.loaded and session.docks and session.all_incidents:
        _precompute_priority_area()
    return {"priority_docks_count": len(names)}


def load_data(
    docks_path: Path,
    incidents_path: Path,
    priority_path: Path,
) -> dict[str, Any]:
    _ensure_backend_cwd()
    if not docks_path.exists():
        raise FileNotFoundError(f"Docks file not found: {docks_path}")
    if not incidents_path.exists():
        raise FileNotFoundError(f"Incidents file not found: {incidents_path}")
    if not priority_path.exists():
        raise FileNotFoundError(f"Priority docks file not found: {priority_path}")

    docks, all_incidents, incidents_in_one_day, priority_dock_names = create_docks_and_incidents(
        str(docks_path),
        str(incidents_path),
        str(priority_path),
    )
    session.priority_dock_names = priority_dock_names

    session.docks = docks
    session.all_incidents = all_incidents
    session.incidents_in_one_day = incidents_in_one_day
    session.active_docks = None
    session.active_incidents = None
    session.area_mode = None
    session.area_bounds = None
    session.analyzed = False
    session.docks_path = docks_path
    session.incidents_path = incidents_path
    session.docks_count = len(docks)
    session.all_incidents_count = len(all_incidents)
    session.full_peak_incidents_count = len(incidents_in_one_day)
    _precompute_priority_area()
    session.loaded = True

    result = {
        "docks_count": len(docks),
        "all_incidents_count": len(all_incidents),
        "full_peak_incidents_count": len(incidents_in_one_day),
        "priority_area_all_incidents_count": session.priority_area_all_incidents_count,
        "priority_area_peak_incidents_count": session.priority_area_peak_incidents_count,
        "docks_file": docks_path.name,
        "incidents_file": incidents_path.name,
        "priority_docks_count": len(session.priority_dock_names),
    }
    return result


def get_status() -> dict[str, Any]:
    return {
        "loaded": session.loaded,
        "analyzed": session.analyzed,
        "area_mode": session.area_mode,
        "docks_count": session.docks_count,
        "all_incidents_count": session.all_incidents_count,
        "full_peak_incidents_count": session.full_peak_incidents_count,
        "priority_area_all_incidents_count": session.priority_area_all_incidents_count,
        "priority_area_peak_incidents_count": session.priority_area_peak_incidents_count,
        "active_docks_count": len(session.active_docks) if session.active_docks else 0,
        "active_incidents_count": len(session.active_incidents) if session.active_incidents else 0,
        "docks_file": session.docks_path.name if session.docks_path else None,
        "incidents_file": session.incidents_path.name if session.incidents_path else None,
        "priority_docks_loaded": bool(session.priority_dock_names),
        "priority_docks_count": len(session.priority_dock_names or []),
    }


def analyze_area(area: str, peak_day_only: bool = False) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    active_docks, active_incidents, area_bounds = _resolve_area_context(area, peak_day_only)

    covered_incidents = [incident for incident in active_incidents if incident.covered_by(active_docks)]
    create_map(
        _priority_dock_names(),
        active_docks,
        active_incidents,
        "docks_and_incidents_map",
        covered_incidents,
        **(area_bounds or {}),
    )

    session.active_docks = active_docks
    session.active_incidents = active_incidents
    session.area_mode = area
    session.area_bounds = area_bounds
    session.analyzed = True

    return {
        "area": area,
        "peak_day_only": peak_day_only,
        "active_docks_count": len(active_docks),
        "active_incidents_count": len(active_incidents),
        "potentially_covered_incidents": len(covered_incidents),
        "map": "docks_and_incidents_map.html",
    }


def _create_optimization_map(
    results: dict,
    incidents: list[Any],
    map_name: str,
    area_bounds: dict[str, float] | None,
) -> str:
    create_map(
        _priority_dock_names(),
        results["selected_docks"],
        incidents,
        map_name,
        results["incidents_covered"],
        results["dock_assignments"],
        **(area_bounds or {}),
    )
    return f"{map_name}.html"


def _run_single_optimization(
    docks: list[Any],
    incidents: list[Any],
    budget: int,
    priority_docks: list[Any] | None,
    percentage_to_cover: float,
) -> dict | None:
    optimizer = MaximizeIncidentsCovered(
        docks=docks,
        incidents=incidents,
        budget=budget,
        priority_docks=priority_docks,
        percentage_incidents_to_cover=percentage_to_cover,
    )
    return optimizer.run()


def run_optimization(
    area: str,
    peak_day_only: bool,
    drone_speed_mph: float = 35.8,
    response_time_minutes: float = 2,
    budget: int = 8,
    open_priority_docks_first: bool = False,
    percentage_mode: str = "single",
    percentage_to_cover: float = 100,
    percentage_range_start: float | None = None,
    percentage_range_end: float | None = None,
    percentage_range_step: float | None = None,
    iterative: bool = False,
    increase_budget: bool = False,
    budget_step: int = 1,
    increase_response_time: bool = False,
    response_time_step: float = 1,
) -> dict[str, Any]:
    _ensure_backend_cwd()

    docks, incidents, area_bounds = _resolve_area_context(area, peak_day_only)
    session.area_mode = area
    session.area_bounds = area_bounds
    session.active_docks = docks
    session.active_incidents = incidents

    initial_response_time = response_time_minutes / 60
    working_docks = clone_docks(
        docks,
        response_time=initial_response_time,
        drone_speed=drone_speed_mph,
    )

    priority_docks = None
    if open_priority_docks_first:
        if not session.priority_dock_names:
            raise ValueError("Upload a priority docks file before opening priority docks first.")
        priority_docks = _priority_docks(working_docks)
        if not priority_docks:
            raise ValueError("No priority docks found in the loaded docks dataset.")

    map_prefix = "priority_docks" if open_priority_docks_first else "optimized"

    if percentage_mode == "range":
        if percentage_range_start is None or percentage_range_end is None or percentage_range_step is None:
            raise ValueError("Percentage range start, end, and step are required.")
        if iterative:
            raise ValueError("Iterative budget/response-time options are not available in range mode.")

        percentages = build_percentage_range_values(
            percentage_range_start,
            percentage_range_end,
            percentage_range_step,
        )
        results_list: list[dict] = []
        outputs: list[str] = []

        for target_percentage in percentages:
            step_results = _run_single_optimization(
                working_docks,
                incidents,
                budget,
                priority_docks,
                target_percentage,
            )
            if step_results is None:
                raise RuntimeError(
                    f"Optimization did not produce a feasible result for {target_percentage:g}%."
                )

            pct_label = str(int(target_percentage)) if float(target_percentage).is_integer() else str(target_percentage)
            outputs.append(
                _create_optimization_map(
                    step_results,
                    incidents,
                    f"{map_prefix}_pct{pct_label}",
                    area_bounds,
                )
            )
            step_results = {**step_results, "target_percentage": target_percentage}
            results_list.append(step_results)

        chart_scenario = f"{map_prefix}_range"
        chart_path = chart_incidents_covered_vs_percentage(
            results_list,
            scenario_name=chart_scenario,
        )
        outputs.append(_relative_output_path(chart_path))
        efficiency_chart_path = chart_dock_efficiency_vs_docks(
            results_list,
            total_incidents=len(incidents),
            scenario_name=chart_scenario,
        )
        outputs.append(_relative_output_path(efficiency_chart_path))

        results = results_list[-1]
        return {
            "scenario": "priority_docks" if open_priority_docks_first else "maximize_coverage",
            "area": area,
            "peak_day_only": peak_day_only,
            "drone_speed_mph": drone_speed_mph,
            "percentage_mode": "range",
            "percentage_range_start": percentage_range_start,
            "percentage_range_end": percentage_range_end,
            "percentage_range_step": percentage_range_step,
            "iterative": False,
            "increase_budget": False,
            "increase_response_time": False,
            "incidents_analyzed": len(incidents),
            "result": _serialize_result(results, target_percentage=results["target_percentage"]),
            "steps": [
                _serialize_result(step, target_percentage=step["target_percentage"])
                for step in results_list
            ],
            "outputs": outputs,
            "map": next((p for p in reversed(outputs) if p.endswith(".html")), None),
        }

    current_budget = budget
    current_response_time = initial_response_time

    results = _run_single_optimization(
        working_docks,
        incidents,
        current_budget,
        priority_docks,
        percentage_to_cover,
    )
    if results is None:
        raise RuntimeError("Optimization did not produce a feasible result.")

    outputs = [
        _create_optimization_map(
            results,
            incidents,
            f"{map_prefix}_map_{current_budget}_docks",
            area_bounds,
        )
    ]
    results_list = [results]

    if iterative and not increase_budget and not increase_response_time:
        raise ValueError("Enable at least one iterative option (budget or response time).")

    if iterative and (increase_budget or increase_response_time):
        incidents_to_cover = len(incidents)
        amount_incidents_covered = results["amount_incidents_covered"]

        while amount_incidents_covered < incidents_to_cover:
            if increase_response_time:
                current_response_time += response_time_step / 60
                working_docks = clone_docks(
                    docks,
                    response_time=current_response_time,
                    drone_speed=drone_speed_mph,
                )
                if priority_docks is not None:
                    priority_docks = _priority_docks(working_docks)
            if increase_budget:
                current_budget += budget_step

            next_results = _run_single_optimization(
                working_docks,
                incidents,
                current_budget,
                priority_docks,
                percentage_to_cover,
            )
            if next_results is None:
                break

            step_label = f"{map_prefix}_step_{current_budget}"
            if increase_response_time:
                response_minutes = round(current_response_time * 60)
                step_label = f"{map_prefix}_rt{response_minutes}m_k{current_budget}"
            outputs.append(
                _create_optimization_map(
                    next_results,
                    incidents,
                    step_label,
                    area_bounds,
                )
            )
            results_list.append(next_results)

            if next_results["amount_incidents_covered"] == amount_incidents_covered:
                break

            amount_incidents_covered = next_results["amount_incidents_covered"]
            results = next_results

        chart_scenario = map_prefix + ("_iterative" if iterative else "")
        chart_path = chart_incidents_covered_vs_k(results_list, scenario_name=chart_scenario)
        outputs.append(_relative_output_path(chart_path))

    return {
        "scenario": "priority_docks" if open_priority_docks_first else "maximize_coverage",
        "area": area,
        "peak_day_only": peak_day_only,
        "drone_speed_mph": drone_speed_mph,
        "percentage_mode": "single",
        "percentage_to_cover": percentage_to_cover,
        "iterative": iterative,
        "increase_budget": increase_budget,
        "budget_step": budget_step,
        "increase_response_time": increase_response_time,
        "response_time_step": response_time_step,
        "incidents_analyzed": len(incidents),
        "result": _serialize_result(results),
        "steps": [_serialize_result(step) for step in results_list],
        "outputs": outputs,
        "map": outputs[0],
    }
