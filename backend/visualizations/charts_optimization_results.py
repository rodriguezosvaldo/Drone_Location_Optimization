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
    covered = [r["incidents_covered"] for r in results]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(ks, covered, marker="o", color=LINE_COLOR, linewidth=2, markersize=8)
    ax.set_xlabel("Number of docks")
    ax.set_ylabel("Incidents covered")
    ax.set_title(
        f"Incidents Covered vs Number of Docks — {SCENARIO_LABELS.get(scenario_name, scenario_name)}"
    )
    ax.grid(True, alpha=0.3)

    for r in results:
        pct = r["coverage_rate"] * 100
        label = f"{r['incidents_covered']:,}\n({pct:.1f}%)"
        ax.annotate(
            label,
            (r["k"], r["incidents_covered"]),
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
