"""
Line chart for optimization results: incidents covered vs number of docks.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BACKEND_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = BACKEND_ROOT.parent / "output" / "figures"
FIG_SIZE = (10, 6)
LINE_COLOR = "#1f77b4"
SCENARIO_LABELS = {
    "no_fixed": "No fixed locations",
    "fixed_metrosafe": "8 MetroSafe docks fixed",
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
