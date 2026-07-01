from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.config import OUTPUT_DIR
from app.services.session import session
from src.docks_and_incidents import (
    create_docks_and_incidents,
    specific_area_docks_and_incidents,
)
from src.optimization_model import maximize_incidents_covered
from visualizations.charts_optimization_results import chart_incidents_covered_vs_k
from visualizations.map_incidents_and_docks import create_map


def _ensure_backend_cwd() -> None:
    backend_root = Path(__file__).resolve().parent.parent.parent
    os.chdir(backend_root)


def _priority_dock_names() -> list[str]:
    return list(session.priority_dock_names or [])


def _priority_docks() -> list[Any]:
    if not session.docks or not session.priority_dock_names:
        return []
    return [dock for dock in session.docks if dock.name in session.priority_dock_names]


def _serialize_result(result: dict) -> dict:
    total = result.get("amount_incidents_covered", 0)
    coverage_rate = result.get("coverage_rate", 0)
    return {
        "k": result["k"],
        "amount_incidents_covered": total,
        "coverage_rate": round(coverage_rate * 100, 2),
        "amount_selected_docks": result["amount_selected_docks"],
        "selected_docks": [d.name for d in result["selected_docks"]],
    }


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
        or session.incidents_in_one_day is None
        or not session.priority_dock_names
    ):
        raise ValueError("Upload incidents, docks, and priority docks files before continuing.")


def _require_analyzed_area() -> None:
    _require_loaded_data()
    if not session.analyzed or session.active_docks is None or session.active_incidents is None:
        raise ValueError("Select and analyze an area before running optimizations.")


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
    session.incidents_count = len(incidents_in_one_day)
    session.loaded = True

    result = {
        "docks_count": len(docks),
        "incidents_count": len(incidents_in_one_day),
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
        "incidents_count": session.incidents_count,
        "active_docks_count": len(session.active_docks) if session.active_docks else 0,
        "active_incidents_count": len(session.active_incidents) if session.active_incidents else 0,
        "docks_file": session.docks_path.name if session.docks_path else None,
        "incidents_file": session.incidents_path.name if session.incidents_path else None,
        "priority_docks_loaded": bool(session.priority_dock_names),
        "priority_docks_count": len(session.priority_dock_names or []),
    }


def analyze_area(area: str) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    if area == "full":
        active_docks = session.docks
        active_incidents = session.incidents_in_one_day
        area_bounds = None
    elif area == "specific":
        if not session.priority_dock_names:
            raise ValueError("Upload a priority docks file before analyzing the priority area.")
        (
            active_docks,
            active_incidents,
            latitude_closest_to_ecuador,
            latitude_farthest_from_ecuador,
            longitude_closest_to_greenwich,
            longitude_farthest_from_greenwich,
        ) = specific_area_docks_and_incidents(
            session.docks,
            session.all_incidents,
            session.priority_dock_names,
        )
        area_bounds = {
            "latitude_closest_to_ecuador": latitude_closest_to_ecuador,
            "latitude_farthest_from_ecuador": latitude_farthest_from_ecuador,
            "longitude_closest_to_greenwich": longitude_closest_to_greenwich,
            "longitude_farthest_from_greenwich": longitude_farthest_from_greenwich,
        }
    else:
        raise ValueError('area must be "full" or "specific".')

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
        "active_docks_count": len(active_docks),
        "active_incidents_count": len(active_incidents),
        "potentially_covered_incidents": len(covered_incidents),
        "map": "docks_and_incidents_map.html",
    }


def _create_optimization_map(
    results: dict,
    map_name: str,
) -> str:
    create_map(
        _priority_dock_names(),
        results["selected_docks"],
        session.active_incidents,
        map_name,
        results["incidents_covered"],
        results["dock_assignments"],
        **_map_kwargs(),
    )
    return f"{map_name}.html"


def run_maximize_optimization(
    dock_locations_quantity: int,
    use_specific_docks: bool = False,
    increase_budget: bool = False,
) -> dict[str, Any]:
    _require_analyzed_area()
    _ensure_backend_cwd()

    docks = session.active_docks
    incidents = session.active_incidents
    specific_docks = None
    if use_specific_docks:
        if not session.priority_dock_names:
            raise ValueError("Upload a priority docks file before prioritizing priority docks.")
        specific_docks = _priority_docks()
        if not specific_docks:
            raise ValueError("No priority docks found in the loaded docks dataset.")

    results = maximize_incidents_covered(
        docks,
        incidents,
        dock_locations_quantity,
        specific_docks,
    )
    if results is None:
        raise RuntimeError("Optimization did not produce a feasible result.")

    if use_specific_docks:
        map_name = f"priority_docks_optimized_map_{dock_locations_quantity}_docks"
    else:
        map_name = f"optimized_map_{dock_locations_quantity}_docks"
    outputs = [_create_optimization_map(results, map_name)]
    results_list = [results]

    amount_incidents_covered = results["amount_incidents_covered"]
    incidents_to_cover = len(incidents)
    current_k = results["k"]

    if increase_budget and amount_incidents_covered < incidents_to_cover:
        while amount_incidents_covered < incidents_to_cover:
            current_k += 1
            next_results = maximize_incidents_covered(
                docks,
                incidents,
                current_k,
                specific_docks,
            )
            if next_results is None:
                break

            if use_specific_docks:
                budget_map_name = f"priority_docks_increase_budget_{current_k}_docks"
            else:
                budget_map_name = f"increase_budget_{current_k}_docks"
            outputs.append(_create_optimization_map(next_results, budget_map_name))
            results_list.append(next_results)

            current_k = next_results["k"]
            if next_results["amount_incidents_covered"] == amount_incidents_covered:
                break
            amount_incidents_covered = next_results["amount_incidents_covered"]
            results = next_results

        chart_scenario = (
            "priority_docks_increase_budget" if use_specific_docks else "increase_budget"
        )
        chart_path = chart_incidents_covered_vs_k(results_list, scenario_name=chart_scenario)
        outputs.append(_relative_output_path(chart_path))

    return {
        "scenario": "priority_docks" if use_specific_docks else "maximize_coverage",
        "area": session.area_mode,
        "increase_budget": increase_budget,
        "result": _serialize_result(results),
        "steps": [_serialize_result(r) for r in results_list],
        "outputs": outputs,
    }
