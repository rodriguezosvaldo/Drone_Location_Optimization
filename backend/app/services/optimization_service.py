from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.config import OUTPUT_DIR
from app.services.session import session
from src.docks_and_incidents import METROSAFE_DOCK_LOCATIONS, create_docks_and_incidents
from src.optimization_model import maximize_incidents_covered, minimize_docks_used
from src.test_multiple_optimizations import (
    compare_optimizations_by_month,
    fixed_locations,
    no_fixed_locations,
)
from visualizations.charts_optimization_results import (
    export_comparison_results,
    export_scenario_results,
)
from visualizations.map_incidents_and_docks import create_map


def _ensure_backend_cwd() -> None:
    backend_root = Path(__file__).resolve().parent.parent.parent
    os.chdir(backend_root)


def _serialize_result(result: dict | None) -> dict | None:
    if result is None:
        return None
    return {
        "k": result.get("k"),
        "incidents_covered": result.get("incidents_covered"),
        "coverage_rate": round(result.get("coverage_rate", 0) * 100, 2),
        "amount_selected_docks": result.get("amount_selected_docks"),
        "selected_docks": [d.name for d in result.get("selected_docks", [])],
    }


def _serialize_results_list(results: list[dict]) -> list[dict]:
    serialized = []
    for entry in results:
        serialized.append(
            {
                "k": entry["k"],
                "incidents_covered": entry["incidents_covered"],
                "coverage_rate": round(entry["coverage_rate"] * 100, 2),
                "delta_coverage": entry.get("delta_coverage", 0),
                "amount_selected_docks": entry["amount_selected_docks"],
                "selected_docks": [d.name for d in entry["selected_docks"]],
            }
        )
    return serialized


def _serialize_monthly_results(results: list[dict]) -> list[dict]:
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    serialized = []
    for entry in results:
        month = entry["month"]
        serialized.append(
            {
                "month": month,
                "month_label": month_names[month - 1] if 1 <= month <= 12 else str(month),
                "peak_day": str(entry["peak_day"]),
                "peak_day_incidents": entry["peak_day_incidents"],
                "incidents_covered": entry["incidents_covered"],
                "coverage_rate": round(entry["coverage_rate"] * 100, 2),
                "amount_selected_docks": entry["amount_selected_docks"],
                "selected_docks": [d.name for d in entry["selected_docks"]],
            }
        )
    return serialized


def _relative_output_path(path: Path) -> str:
    try:
        return str(path.relative_to(OUTPUT_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _collect_output_files(prefix: str | None = None) -> list[str]:
    files: list[str] = []
    for folder in (OUTPUT_DIR, OUTPUT_DIR / "figures", OUTPUT_DIR / "tables"):
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_file():
                rel = _relative_output_path(path)
                if prefix is None or Path(rel).name.startswith(prefix):
                    files.append(rel)
    return sorted(files)


def _require_loaded_data() -> None:
    if not session.loaded or session.docks is None or session.incidents is None:
        raise ValueError("Load docks and incidents data before running optimizations.")


def load_data(docks_path: Path, incidents_path: Path) -> dict[str, Any]:
    _ensure_backend_cwd()
    if not docks_path.exists():
        raise FileNotFoundError(f"Docks file not found: {docks_path}")
    if not incidents_path.exists():
        raise FileNotFoundError(f"Incidents file not found: {incidents_path}")

    docks, incidents, incidents_by_month = create_docks_and_incidents(
        str(docks_path),
        str(incidents_path),
    )
    create_map(docks, incidents, "docks_and_incidents_map")

    session.docks = docks
    session.incidents = incidents
    session.incidents_by_month = incidents_by_month
    session.docks_path = docks_path
    session.incidents_path = incidents_path
    session.docks_count = len(docks)
    session.incidents_count = len(incidents)
    session.loaded = True

    return {
        "docks_count": len(docks),
        "incidents_count": len(incidents),
        "docks_file": str(docks_path.name),
        "incidents_file": str(incidents_path.name),
        "map": "docks_and_incidents_map.html",
    }


def get_status() -> dict[str, Any]:
    return {
        "loaded": session.loaded,
        "docks_count": session.docks_count,
        "incidents_count": session.incidents_count,
        "docks_file": session.docks_path.name if session.docks_path else None,
        "incidents_file": session.incidents_path.name if session.incidents_path else None,
        "metrosafe_fixed_docks": len(METROSAFE_DOCK_LOCATIONS),
    }


def run_single_optimization(
    dock_locations_quantity: int,
    max_dock_coverage_capacity: int,
    generate_map: bool = True,
) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    result = maximize_incidents_covered(
        session.docks,
        session.incidents,
        dock_locations_quantity,
        max_dock_coverage_capacity,
    )
    if result is None:
        raise RuntimeError("Optimization did not produce a feasible result.")

    outputs = []
    if generate_map:
        create_map(
            result["selected_docks"],
            result["covered_incidents"],
            "optimized_map",
            all_incidents=session.incidents,
            covered_incidents=result["covered_incidents"],
        )
        outputs.append("optimized_map.html")

    return {
        "result": _serialize_result(result),
        "outputs": outputs,
    }


def run_minimize_docks(
    dock_locations_quantity: int,
    max_dock_coverage_capacity: int,
    generate_map: bool = True,
) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    result = minimize_docks_used(
        session.docks,
        session.incidents,
        dock_locations_quantity,
        max_dock_coverage_capacity,
    )
    if result is None:
        raise RuntimeError("Dock minimization did not produce a feasible result.")

    outputs = []
    if generate_map:
        create_map(
            result["selected_docks"],
            result["covered_incidents"],
            "minimized_docks_map",
            all_incidents=session.incidents,
            covered_incidents=result["covered_incidents"],
        )
        outputs.append("minimized_docks_map.html")

    return {
        "result": _serialize_result(result),
        "outputs": outputs,
    }


def run_no_fixed_scenario(
    k_min: int,
    k_max: int,
    max_dock_coverage_capacity: int,
) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    results = no_fixed_locations(
        session.docks,
        session.incidents,
        k_min,
        k_max,
        k_max,
        max_dock_coverage_capacity,
    )
    export_scenario_results("no_fixed", results, session.incidents)
    return {
        "scenario": "no_fixed",
        "results": _serialize_results_list(results),
        "outputs": _collect_output_files("optimization_"),
    }


def run_fixed_scenario(
    k_max: int,
    max_dock_coverage_capacity: int,
) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    if k_max < len(METROSAFE_DOCK_LOCATIONS):
        raise ValueError(
            f"k_max must be at least {len(METROSAFE_DOCK_LOCATIONS)} (MetroSafe fixed docks)."
        )

    results = fixed_locations(
        session.docks,
        session.incidents,
        k_max,
        k_max,
        max_dock_coverage_capacity,
    )
    export_scenario_results("fixed_metrosafe", results, session.incidents)
    return {
        "scenario": "fixed_metrosafe",
        "results": _serialize_results_list(results),
        "outputs": _collect_output_files("optimization_"),
    }


def run_compare_both_scenarios(
    k_min: int,
    k_max: int,
    max_dock_coverage_capacity: int,
) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    if k_max < len(METROSAFE_DOCK_LOCATIONS):
        raise ValueError(
            f"k_max must be at least {len(METROSAFE_DOCK_LOCATIONS)} (MetroSafe fixed docks)."
        )

    results_no_fixed = no_fixed_locations(
        session.docks,
        session.incidents,
        k_min,
        k_max,
        k_max,
        max_dock_coverage_capacity,
    )
    results_fixed = fixed_locations(
        session.docks,
        session.incidents,
        k_max,
        k_max,
        max_dock_coverage_capacity,
    )
    export_scenario_results("no_fixed", results_no_fixed, session.incidents)
    export_scenario_results("fixed_metrosafe", results_fixed, session.incidents)
    export_comparison_results(
        {
            "no_fixed": results_no_fixed,
            "fixed_metrosafe": results_fixed,
        }
    )

    return {
        "no_fixed": _serialize_results_list(results_no_fixed),
        "fixed_metrosafe": _serialize_results_list(results_fixed),
        "outputs": _collect_output_files("optimization_"),
    }


def run_monthly_comparison(
    dock_locations_quantity: int,
    max_dock_coverage_capacity: int,
) -> dict[str, Any]:
    _require_loaded_data()
    _ensure_backend_cwd()

    results = compare_optimizations_by_month(
        session.docks,
        session.incidents_by_month,
        dock_locations_quantity,
        max_dock_coverage_capacity,
    )
    return {
        "results": _serialize_monthly_results(results),
        "outputs": _collect_output_files("optimization_incidents_covered_by_month"),
    }
