"""
Charts, tables, and map exports for multi-run dock optimization results.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from visualizations.map_incidents_and_docks import create_map

FIGURES_DIR = PROJECT_ROOT / "output" / "figures"
TABLES_DIR = PROJECT_ROOT / "output" / "tables"
MAPS_DIR = PROJECT_ROOT / "output"

FIG_SIZE = (10, 6)
BAR_COLOR = "#1f77b4"
LINE_COLOR = "#1f77b4"
SCENARIO_COLORS = {
    "no_fixed": "#1f77b4",
    "fixed_metrosafe": "#ff7f0e",
}
SCENARIO_LABELS = {
    "no_fixed": "No fixed locations",
    "fixed_metrosafe": "8 MetroSafe docks fixed",
}
MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _ensure_output_dirs() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)


def _comparable_delta_results(results: list[dict]) -> list[dict]:
    """Skip the first result: delta vs a prior k is undefined for the initial run."""
    return results[1:] if len(results) > 1 else []


def _results_lookup(results: list[dict]) -> dict[int, dict]:
    return {r["k"]: r for r in results}


def _common_ks(*results_lists: list[dict]) -> list[int]:
    lookups = [_results_lookup(results) for results in results_lists if results]
    if len(lookups) < 2:
        return []
    common = set(lookups[0])
    for lookup in lookups[1:]:
        common &= set(lookup)
    return sorted(common)


def results_to_dataframe(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append(
            {
                "k": r["k"],
                "incidents_covered": r["incidents_covered"],
                "coverage_rate_pct": round(r["coverage_rate"] * 100, 2),
                "delta_coverage": r.get("delta_coverage", 0),
                "amount_selected_docks": r["amount_selected_docks"],
            }
        )
    return pd.DataFrame(rows)


def chart_incidents_covered_vs_k(
    results: list[dict],
    *,
    scenario_name: str,
    output_path: Path | None = None,
) -> Path:
    """Line chart: incidents covered vs k."""
    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / f"optimization_incidents_covered_{scenario_name}.png"

    ks = [r["k"] for r in results]
    covered = [r["incidents_covered"] for r in results]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(ks, covered, marker="o", color=LINE_COLOR, linewidth=2, markersize=8)
    ax.set_xlabel("Number of docks (k)")
    ax.set_ylabel("Incidents covered")
    ax.set_title(f"Incidents Covered vs Number of Docks — {SCENARIO_LABELS.get(scenario_name, scenario_name)}")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def chart_coverage_rate_vs_k(
    results: list[dict],
    *,
    scenario_name: str,
    output_path: Path | None = None,
) -> Path:
    """Line chart: coverage rate (%) vs k."""
    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / f"optimization_coverage_rate_{scenario_name}.png"

    ks = [r["k"] for r in results]
    rates = [r["coverage_rate"] * 100 for r in results]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(ks, rates, marker="o", color=LINE_COLOR, linewidth=2, markersize=8)
    ax.set_xlabel("Number of docks (k)")
    ax.set_ylabel("Coverage rate (%)")
    ax.set_title(f"Coverage Rate vs Number of Docks — {SCENARIO_LABELS.get(scenario_name, scenario_name)}")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def chart_delta_coverage_vs_k(
    results: list[dict],
    *,
    scenario_name: str,
    output_path: Path | None = None,
) -> Path | None:
    """Bar chart: marginal coverage gain per k (excludes the first k, not comparable)."""
    comparable = _comparable_delta_results(results)
    if not comparable:
        return None

    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / f"optimization_delta_coverage_{scenario_name}.png"

    ks = [r["k"] for r in comparable]
    deltas = [r.get("delta_coverage", 0) for r in comparable]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.bar(ks, deltas, color=BAR_COLOR, edgecolor="navy", alpha=0.85, width=0.7)
    ax.set_xlabel("Number of docks (k)")
    ax.set_ylabel("Additional incidents covered (delta)")
    ax.set_title(f"Marginal Coverage Gain vs Number of Docks — {SCENARIO_LABELS.get(scenario_name, scenario_name)}")
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def chart_scenario_comparison(
    results_by_scenario: dict[str, list[dict]],
    *,
    output_path: Path | None = None,
) -> Path:
    """Overlaid line chart comparing incidents covered across scenarios."""
    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / "optimization_scenario_comparison.png"

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    for scenario_name, results in results_by_scenario.items():
        if not results:
            continue
        ks = [r["k"] for r in results]
        covered = [r["incidents_covered"] for r in results]
        color = SCENARIO_COLORS.get(scenario_name, None)
        label = SCENARIO_LABELS.get(scenario_name, scenario_name)
        ax.plot(ks, covered, marker="o", linewidth=2, markersize=7, color=color, label=label)

    ax.set_xlabel("Number of docks (k)")
    ax.set_ylabel("Incidents covered")
    ax.set_title("Scenario Comparison: Incidents Covered vs Number of Docks")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def chart_scenario_coverage_rate_comparison(
    results_by_scenario: dict[str, list[dict]],
    *,
    output_path: Path | None = None,
) -> Path:
    """Overlaid line chart comparing coverage rate (%) across scenarios."""
    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / "optimization_scenario_coverage_rate_comparison.png"

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    for scenario_name, results in results_by_scenario.items():
        if not results:
            continue
        ks = [r["k"] for r in results]
        rates = [r["coverage_rate"] * 100 for r in results]
        color = SCENARIO_COLORS.get(scenario_name, None)
        label = SCENARIO_LABELS.get(scenario_name, scenario_name)
        ax.plot(ks, rates, marker="o", linewidth=2, markersize=7, color=color, label=label)

    ax.set_xlabel("Number of docks (k)")
    ax.set_ylabel("Coverage rate (%)")
    ax.set_title("Scenario Comparison: Coverage Rate vs Number of Docks")
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def chart_scenario_incidents_gap(
    results_by_scenario: dict[str, list[dict]],
    *,
    baseline_scenario: str = "fixed_metrosafe",
    comparison_scenario: str = "no_fixed",
    output_path: Path | None = None,
) -> Path | None:
    """Line chart of incidents-covered gap between scenarios at shared k values."""
    baseline = results_by_scenario.get(baseline_scenario, [])
    comparison = results_by_scenario.get(comparison_scenario, [])
    common_ks = _common_ks(baseline, comparison)
    if not common_ks:
        return None

    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / "optimization_scenario_incidents_gap.png"

    baseline_by_k = _results_lookup(baseline)
    comparison_by_k = _results_lookup(comparison)
    gaps = [comparison_by_k[k]["incidents_covered"] - baseline_by_k[k]["incidents_covered"] for k in common_ks]

    baseline_label = SCENARIO_LABELS.get(baseline_scenario, baseline_scenario)
    comparison_label = SCENARIO_LABELS.get(comparison_scenario, comparison_scenario)

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.axhline(0, color="gray", linewidth=1, linestyle="--", alpha=0.7)
    ax.plot(common_ks, gaps, marker="o", color="#2ca02c", linewidth=2, markersize=7)
    ax.fill_between(
        common_ks,
        gaps,
        0,
        where=[g >= 0 for g in gaps],
        color="#2ca02c",
        alpha=0.15,
        interpolate=True,
    )
    ax.fill_between(
        common_ks,
        gaps,
        0,
        where=[g < 0 for g in gaps],
        color="#d62728",
        alpha=0.15,
        interpolate=True,
    )
    ax.set_xlabel("Number of docks (k)")
    ax.set_ylabel("Incidents covered gap")
    ax.set_title(
        f"Scenario Gap: {comparison_label} minus {baseline_label}\n"
        "(positive = more incidents covered without fixed MetroSafe docks)"
    )
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def chart_scenario_marginal_gain_comparison(
    results_by_scenario: dict[str, list[dict]],
    *,
    output_path: Path | None = None,
) -> Path | None:
    """Grouped bar chart comparing marginal coverage gains at shared k values (k > first)."""
    comparable_by_scenario = {
        name: _comparable_delta_results(results)
        for name, results in results_by_scenario.items()
        if results
    }
    if len(comparable_by_scenario) < 2:
        return None

    lookups = {name: _results_lookup(results) for name, results in comparable_by_scenario.items()}
    common_ks = _common_ks(*comparable_by_scenario.values())
    if not common_ks:
        return None

    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / "optimization_scenario_marginal_gain_comparison.png"

    n_scenarios = len(lookups)
    bar_width = 0.8 / n_scenarios
    x = range(len(common_ks))

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    for i, (scenario_name, lookup) in enumerate(lookups.items()):
        offsets = [xi + (i - (n_scenarios - 1) / 2) * bar_width for xi in x]
        deltas = [lookup[k].get("delta_coverage", 0) for k in common_ks]
        color = SCENARIO_COLORS.get(scenario_name, None)
        label = SCENARIO_LABELS.get(scenario_name, scenario_name)
        ax.bar(offsets, deltas, width=bar_width, color=color, edgecolor="black", alpha=0.85, label=label)

    ax.set_xlabel("Number of docks (k)")
    ax.set_ylabel("Additional incidents covered (delta)")
    ax.set_title("Scenario Comparison: Marginal Coverage Gain per Additional Dock")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(k) for k in common_ks])
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def export_results_table(
    results: list[dict],
    *,
    scenario_name: str,
    output_path: Path | None = None,
) -> Path:
    """Export optimization results to Excel."""
    _ensure_output_dirs()
    output_path = output_path or TABLES_DIR / f"optimization_results_{scenario_name}.xlsx"
    df = results_to_dataframe(results)
    df.to_excel(output_path, index=False, sheet_name="results")
    return output_path


def export_best_configuration_map(
    results: list[dict],
    incidents,
    *,
    scenario_name: str,
    output_name: str | None = None,
) -> Path | None:
    """Create a map for the configuration with the highest incidents covered."""
    _ensure_output_dirs()
    if not results:
        return None

    best = max(results, key=lambda r: r["incidents_covered"])
    selected_docks = best.get("selected_docks")
    if not selected_docks:
        return None

    map_name = output_name or f"optimization_map_{scenario_name}_k{best['k']}"
    covered_incidents = best.get("covered_incidents", [])
    create_map(
        selected_docks,
        covered_incidents,
        map_name,
        all_incidents=incidents,
        covered_incidents=covered_incidents,
    )
    return MAPS_DIR / f"{map_name}.html"


def export_scenario_results(
    scenario_name: str,
    results: list[dict],
    incidents,
) -> dict[str, Path]:
    """Export all charts, table, and best-configuration map for one scenario."""
    if not results:
        print(f"No results to export for scenario '{scenario_name}'.")
        return {}

    paths = {
        "incidents_chart": chart_incidents_covered_vs_k(results, scenario_name=scenario_name),
        "coverage_rate_chart": chart_coverage_rate_vs_k(results, scenario_name=scenario_name),
        "table": export_results_table(results, scenario_name=scenario_name),
    }
    delta_path = chart_delta_coverage_vs_k(results, scenario_name=scenario_name)
    if delta_path:
        paths["delta_chart"] = delta_path
    map_path = export_best_configuration_map(results, incidents, scenario_name=scenario_name)
    if map_path:
        paths["map"] = map_path

    print(f"\nExported results for '{SCENARIO_LABELS.get(scenario_name, scenario_name)}':")
    for label, path in paths.items():
        print(f"  {label}: {path}")

    return paths


def chart_incidents_covered_by_month(
    monthly_results: list[dict],
    *,
    dock_locations_quantity: int,
    output_path: Path | None = None,
) -> Path | None:
    """Line chart: incidents covered vs month (peak day per month)."""
    if not monthly_results:
        return None

    _ensure_output_dirs()
    output_path = output_path or FIGURES_DIR / "optimization_incidents_covered_by_month.png"

    months = [r["month"] for r in monthly_results]
    covered = [r["incidents_covered"] for r in monthly_results]
    month_names = [MONTH_LABELS[m - 1] for m in months]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(months, covered, marker="o", color=LINE_COLOR, linewidth=2, markersize=8)
    ax.set_xticks(months)
    ax.set_xticklabels(month_names)
    ax.set_xlabel("Month")
    ax.set_ylabel("Incidents covered")
    ax.set_title(
        "Incidents Covered by Month (Peak Day)\n"
        f"Optimized with up to {dock_locations_quantity} dock location(s)"
    )
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def export_monthly_comparison_results(
    monthly_results: list[dict],
    *,
    dock_locations_quantity: int,
) -> dict[str, Path]:
    """Export monthly peak-day optimization chart and table."""
    if not monthly_results:
        print("No monthly optimization results to export.")
        return {}

    _ensure_output_dirs()
    paths: dict[str, Path] = {}

    chart_path = chart_incidents_covered_by_month(
        monthly_results,
        dock_locations_quantity=dock_locations_quantity,
    )
    if chart_path:
        paths["incidents_by_month_chart"] = chart_path

    table_path = TABLES_DIR / "optimization_results_by_month_peak_day.xlsx"
    df = pd.DataFrame(
        [
            {
                "month": r["month"],
                "month_label": MONTH_LABELS[r["month"] - 1],
                "peak_day": r["peak_day"],
                "peak_day_incidents": r["peak_day_incidents"],
                "incidents_covered": r["incidents_covered"],
                "coverage_rate_pct": round(r["coverage_rate"] * 100, 2),
                "amount_selected_docks": r["amount_selected_docks"],
                "dock_locations_quantity": dock_locations_quantity,
            }
            for r in monthly_results
        ]
    )
    df.to_excel(table_path, index=False, sheet_name="peak_day_by_month")
    paths["table"] = table_path

    print("\nExported monthly peak-day optimization results:")
    for label, path in paths.items():
        print(f"  {label}: {path}")

    return paths


def export_comparison_results(results_by_scenario: dict[str, list[dict]]) -> dict[str, Path]:
    """Export scenario comparison charts (overlay, gap, coverage %, marginal gains)."""
    if len(results_by_scenario) < 2 or not any(results_by_scenario.values()):
        return {}

    paths: dict[str, Path] = {
        "scenario_comparison": chart_scenario_comparison(results_by_scenario),
        "coverage_rate_comparison": chart_scenario_coverage_rate_comparison(results_by_scenario),
    }
    gap_path = chart_scenario_incidents_gap(results_by_scenario)
    if gap_path:
        paths["incidents_gap"] = gap_path
    marginal_path = chart_scenario_marginal_gain_comparison(results_by_scenario)
    if marginal_path:
        paths["marginal_gain_comparison"] = marginal_path

    print("\nExported scenario comparison charts:")
    for label, path in paths.items():
        print(f"  {label}: {path}")
    return paths
