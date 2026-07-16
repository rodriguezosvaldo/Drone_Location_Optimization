"""
Line chart for optimization results: incidents covered vs number of docks.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

BACKEND_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = BACKEND_ROOT.parent / "output" / "figures"
FIG_SIZE = (10, 6)
LINE_COLOR = "#1f77b4"
COMPARISON_FREE_COLOR = "#1a7f37"
COMPARISON_PREF_COLOR = "#ff7f0e"
SCENARIO_LABELS = {
    "no_fixed": "No fixed locations",
    "fixed_metrosafe": "8 MetroSafe docks fixed",
    "maximize_coverage": "Open docks freely",
    "priority_docks": "Open MetroSafe docks first",
}


def _covered_count(result: dict) -> int:
    if "amount_incidents_covered" in result:
        return result["amount_incidents_covered"]
    value = result["incidents_covered"]
    return len(value) if isinstance(value, (list, tuple, set)) else int(value)


def _dock_count(result: dict, *, use_selected: bool) -> int:
    if use_selected:
        return result["amount_selected_docks"]
    return result["k"]


def chart_incidents_covered_vs_k(
    results: list[dict],
    *,
    scenario_name: str,
    output_path: Path | None = None,
    show: bool = False,
) -> Path:
    """Line chart: docks (x) vs incidents covered (y), with count and % of total at each point."""
    if not results:
        raise ValueError("results must contain at least one optimization run.")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    save_path = output_path or FIGURES_DIR / f"optimization_incidents_covered_{scenario_name}.png"

    ks = [r["k"] for r in results]
    covered = [_covered_count(r) for r in results]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(ks, covered, marker="o", color=LINE_COLOR, linewidth=2, markersize=8)
    ax.set_xlabel("Number of docks")
    ax.set_ylabel("Incidents covered")
    ax.set_title(
        f"Incidents Covered vs Number of Docks — {SCENARIO_LABELS.get(scenario_name, scenario_name)}"
    )
    ax.grid(True, alpha=0.3)

    for r, count in zip(results, covered):
        pct = r["coverage_rate"] * 100
        label = f"{count:,}\n({pct:.1f}%)"
        ax.annotate(
            label,
            (r["k"], count),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
        )

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    if show:
        plt.show()
    else:
        plt.close(fig)
    return save_path


def chart_incidents_covered_vs_percentage(
    results: list[dict],
    *,
    scenario_name: str,
    output_path: Path | None = None,
    show: bool = False,
) -> Path:
    """Line chart: target coverage percentage (x) vs incidents covered (y)."""
    if not results:
        raise ValueError("results must contain at least one optimization run.")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    save_path = output_path or FIGURES_DIR / f"optimization_incidents_covered_{scenario_name}.png"

    percentages = [r["target_percentage"] for r in results]
    covered = [_covered_count(r) for r in results]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(percentages, covered, marker="o", color=LINE_COLOR, linewidth=2, markersize=8)
    ax.set_xlabel("Target percentage to cover")
    ax.set_ylabel("Incidents covered")
    ax.set_title(
        f"Incidents Covered vs Target Percentage — {SCENARIO_LABELS.get(scenario_name, scenario_name)}"
    )
    ax.grid(True, alpha=0.3)

    for r, count in zip(results, covered):
        pct = r["coverage_rate"] * 100
        label = f"{count:,}\n({pct:.1f}%)"
        ax.annotate(
            label,
            (r["target_percentage"], count),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
        )

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    if show:
        plt.show()
    else:
        plt.close(fig)
    return save_path


def chart_dock_efficiency_vs_docks(
    results: list[dict],
    *,
    total_incidents: int,
    scenario_name: str,
    output_path: Path | None = None,
    show: bool = False,
) -> Path:
    """Line chart: dock index (x) vs each dock's share of total incidents covered (y)."""
    if not results:
        raise ValueError("results must contain at least one optimization run.")
    if total_incidents <= 0:
        raise ValueError("total_incidents must be greater than zero.")

    best_result = max(
        results,
        key=lambda r: (_covered_count(r), _dock_count(r, use_selected=True)),
    )
    assignments = best_result.get("dock_assignments") or {}
    dock_efficiencies = sorted(
        (
            len(incidents) / total_incidents * 100
            for incidents in assignments.values()
            if incidents
        ),
        reverse=True,
    )

    if not dock_efficiencies:
        raise ValueError("No dock assignments available to plot efficiency.")

    dock_indices = list(range(1, len(dock_efficiencies) + 1))

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    save_path = output_path or FIGURES_DIR / f"optimization_dock_efficiency_{scenario_name}.png"

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(dock_indices, dock_efficiencies, marker="o", color=LINE_COLOR, linewidth=2, markersize=8)
    ax.set_xlabel("Docks")
    ax.set_ylabel("Efficiency (% of total incidents covered)")
    ax.set_title(
        f"Dock Efficiency vs Docks — {SCENARIO_LABELS.get(scenario_name, scenario_name)}"
    )
    ymax = max(dock_efficiencies)
    ax.set_ylim(0, min(105, ymax + 5))
    ax.set_xticks(dock_indices)
    ax.grid(True, alpha=0.3)

    for dock_index, efficiency in zip(dock_indices, dock_efficiencies):
        ax.annotate(
            f"{efficiency:.1f}%",
            (dock_index, efficiency),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
        )

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    if show:
        plt.show()
    else:
        plt.close(fig)
    return save_path


def _coverage_pcts(results: list[dict]) -> list[float]:
    """Normalize coverage to 0–100 percentages for a full series."""
    rates = [float(r.get("coverage_rate", 0) or 0) for r in results]
    if rates and max(rates) <= 1.0:
        return [rate * 100 for rate in rates]
    return rates


def _series_xy(
    results: list[dict],
    *,
    chart_mode: str,
) -> tuple[list[float], list[float], list[float]]:
    """Return (x, y, coverage_pct) for a comparison series."""
    coverages = _coverage_pcts(results)
    xs: list[float] = []
    ys: list[float] = []
    for r, coverage in zip(results, coverages):
        docks = float(r.get("amount_selected_docks", r.get("k", 0)) or 0)
        if chart_mode == "response_time":
            x = float(r.get("response_time_minutes", 0) or 0)
            y = docks
        elif chart_mode == "budget":
            x = docks
            y = coverage
        else:
            x = float(r.get("k", docks) or 0)
            y = float(_covered_count(r))
        xs.append(x)
        ys.append(y)
    return xs, ys, coverages


def _resolve_scenario_label(scenario: str | None, fallback: str) -> str:
    if not scenario:
        return fallback
    return SCENARIO_LABELS.get(scenario, fallback)


def chart_compare_two_scenarios(
    results_a: list[dict],
    results_b: list[dict],
    *,
    label_a: str = "Scenario 1",
    label_b: str = "Scenario 2",
    scenario_a: str | None = None,
    scenario_b: str | None = None,
    chart_mode: str = "budget",
    output_path: Path | None = None,
    show: bool = False,
) -> Path:
    """
    Overlay two optimization result series on one comparison chart.

    chart_mode:
      - "budget": docks opened (x) vs coverage % (y) — matches charts_increase_budget.py
      - "response_time": response time (x) vs docks opened (y) — matches charts_increase_response_time.py
      - "incidents_vs_k": docks budget (x) vs incidents covered (y)
    """
    if not results_a or not results_b:
        raise ValueError("Both scenarios must include at least one result step.")

    resolved_a = _resolve_scenario_label(scenario_a, label_a)
    resolved_b = _resolve_scenario_label(scenario_b, label_b)
    if resolved_a == resolved_b:
        resolved_a = label_a
        resolved_b = label_b

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    save_path = output_path or FIGURES_DIR / "optimization_compare_scenarios.png"

    series = [
        (results_a, COMPARISON_FREE_COLOR, resolved_a, 7),
        (results_b, COMPARISON_PREF_COLOR, resolved_b, 9),
    ]

    fig, ax = plt.subplots(figsize=(12, 7))
    for results, color, label, markersize in series:
        xs, ys, coverages = _series_xy(results, chart_mode=chart_mode)
        ax.plot(
            xs,
            ys,
            color=color,
            linewidth=2.5 if color == COMPARISON_FREE_COLOR else 3.0,
            marker="o",
            markersize=markersize,
            markerfacecolor=color,
            markeredgecolor="white",
            markeredgewidth=1.2,
            label=label,
            zorder=4,
        )
        for x, y, coverage in zip(xs, ys, coverages):
            if chart_mode in ("budget", "response_time"):
                text = f"{coverage:.1f}%"
            else:
                text = f"{int(y):,}\n({coverage:.1f}%)"
            ax.annotate(
                text,
                (x, y),
                textcoords="offset points",
                xytext=(0, 10) if color == COMPARISON_FREE_COLOR else (0, -14),
                ha="center",
                va="bottom" if color == COMPARISON_FREE_COLOR else "top",
                fontsize=8,
                color=color,
            )

    if chart_mode == "budget":
        ax.set_xlabel("Number of docks opened")
        ax.set_ylabel("Percentage of incidents covered")
        ax.set_title("Docks Opened vs Percentage of Incidents Covered")
        ax.set_ylim(0, 105)
    elif chart_mode == "response_time":
        ax.set_xlabel("Response time (minutes)")
        ax.set_ylabel("Number of docks opened")
        ax.set_title("Docks Opened vs Response Time")
    else:
        ax.set_xlabel("Number of docks")
        ax.set_ylabel("Incidents covered")
        ax.set_title("Incidents Covered vs Number of Docks — Comparison")

    ax.grid(True, alpha=0.3)
    legend_handles = [
        Line2D(
            [0],
            [0],
            color=COMPARISON_FREE_COLOR,
            linewidth=2.5,
            marker="o",
            markersize=7,
            label=resolved_a,
        ),
        Line2D(
            [0],
            [0],
            color=COMPARISON_PREF_COLOR,
            linewidth=3.0,
            marker="o",
            markersize=9,
            label=resolved_b,
        ),
    ]
    ax.legend(handles=legend_handles, loc="best", framealpha=0.95)
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    if show:
        plt.show()
    else:
        plt.close(fig)
    return save_path
