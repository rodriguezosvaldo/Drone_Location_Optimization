"""
Generate Docks Opened vs % Incidents Covered chart from tables_increase_budget.xlsx.

Expected columns (header row):
  - budget
  - Coverage (%)
  - Total docks opened
  - MetroSafe docks opened
  - JCPS docks opened

X-axis: docks opened. A second axis below shows the budget at each docks value.
Y-axis: percentage of incidents covered.

If a second table starts at column G, also generate a comparison line chart
for both scenarios.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "tables_increase_budget.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "figures" / "docks_opened_vs_coverage.png"
DEFAULT_COMPARISON_OUTPUT = (
    PROJECT_ROOT / "output" / "figures" / "docks_opened_vs_coverage_comparison.png"
)

COVERAGE_LINE_COLOR = "#1a7f37"
COMPARISON_FREE_COLOR = "#1a7f37"
COMPARISON_PREF_COLOR = "#ff7f0e"
FIG_SIZE = (12, 7)
BUDGET_AXIS_OFFSET = 42

# Excel column G is 0-indexed column 6.
SECOND_TABLE_START_COL = 6

COLUMN_ALIASES = {
    "budget": ["budget", "k", "budget (docks)", "docks budget"],
    "coverage": ["coverage (%)", "coverage", "coverage_pct", "covered", "covered (%)"],
    "total": ["total docks opened", "total", "total_docks_opened"],
    "metrosafe": ["metrosafe docks opened", "metrosafe", "metrosafe_docks_opened"],
    "jcps": ["jcps docks opened", "jcps", "jcps_docks_opened"],
}


def _normalize_column_name(name: object) -> str:
    return " ".join(str(name).strip().lower().replace("_", " ").split())


def _is_budget_header(value: object) -> bool:
    return _normalize_column_name(value) in COLUMN_ALIASES["budget"]


def _find_header_row(raw: pd.DataFrame) -> int | None:
    for row_idx in range(len(raw)):
        row_values = {_normalize_column_name(v) for v in raw.iloc[row_idx].tolist() if pd.notna(v)}
        if any(alias in row_values for aliases in COLUMN_ALIASES.values() for alias in aliases):
            return row_idx
    return None


def _resolve_column(columns: list[str], key: str) -> str:
    normalized = {_normalize_column_name(col): col for col in columns}
    for alias in COLUMN_ALIASES[key]:
        if alias in normalized:
            return normalized[alias]
    raise KeyError(
        f"Missing column for '{key}'. Found: {columns}. "
        f"Expected one of: {COLUMN_ALIASES[key]}"
    )


def _parse_table_block(block: pd.DataFrame) -> pd.DataFrame:
    """Parse a raw block (no header set) into a normalized chart DataFrame."""
    if block.empty:
        raise ValueError("Empty table block")

    header_row = _find_header_row(block)
    if header_row is None:
        raise ValueError(
            "Could not find a header row. "
            "Expected columns such as 'budget' and 'Total docks opened'."
        )

    headers = [
        str(v).strip() if pd.notna(v) else f"col_{i}"
        for i, v in enumerate(block.iloc[header_row].tolist())
    ]
    df = block.iloc[header_row + 1 :].copy()
    df.columns = headers
    df = df.dropna(how="all")

    budget_col = _resolve_column(df.columns.tolist(), "budget")
    coverage_col = _resolve_column(df.columns.tolist(), "coverage")
    total_col = _resolve_column(df.columns.tolist(), "total")
    metrosafe_col = _resolve_column(df.columns.tolist(), "metrosafe")
    jcps_col = _resolve_column(df.columns.tolist(), "jcps")

    chart_df = pd.DataFrame(
        {
            "budget": pd.to_numeric(df[budget_col], errors="coerce"),
            "coverage": pd.to_numeric(df[coverage_col], errors="coerce"),
            "total": pd.to_numeric(df[total_col], errors="coerce"),
            "metrosafe": pd.to_numeric(df[metrosafe_col], errors="coerce"),
            "jcps": pd.to_numeric(df[jcps_col], errors="coerce"),
        }
    )
    chart_df = chart_df.dropna(subset=["budget", "coverage", "total", "metrosafe", "jcps"])
    chart_df = chart_df.sort_values("total").reset_index(drop=True)

    if chart_df.empty:
        raise ValueError("No valid numeric rows found in table block")

    return chart_df


def _has_second_table_from_column_g(raw: pd.DataFrame) -> bool:
    """True when a second header table begins at Excel column G (index 6)."""
    if raw.shape[1] <= SECOND_TABLE_START_COL:
        return False

    right = raw.iloc[:, SECOND_TABLE_START_COL:]
    for row_idx in range(len(right)):
        first_cell = right.iloc[row_idx, 0]
        if _is_budget_header(first_cell):
            return True
    return False


def load_chart_tables(
    input_path: Path | str = DEFAULT_INPUT,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """
    Load chart data from Excel.

    Returns (primary_table, secondary_table_or_None).
    Primary table is always the leftmost block (from column A).
    Secondary table is loaded only when a second table starts at column G.
    """
    path = Path(input_path)
    raw = pd.read_excel(path, header=None)
    if raw.empty:
        raise ValueError(f"No data found in {path}")

    if _has_second_table_from_column_g(raw):
        left = raw.iloc[:, :SECOND_TABLE_START_COL]
        # Drop fully empty separator columns on the left block.
        left = left.dropna(axis=1, how="all")
        right = raw.iloc[:, SECOND_TABLE_START_COL:]
        return _parse_table_block(left), _parse_table_block(right)

    return _parse_table_block(raw), None


def load_chart_data(input_path: Path | str = DEFAULT_INPUT) -> pd.DataFrame:
    """Load the primary (leftmost) chart table. Kept for backward compatibility."""
    primary, _ = load_chart_tables(input_path)
    return primary


def _format_coverage_label(cov: float) -> str:
    return f"{cov:.0f}%" if cov == int(cov) else f"{cov:.1f}%"


def _format_budget_label(budget: float) -> str:
    return f"{budget:.0f}" if budget == int(budget) else f"{budget:g}"


def _annotate_coverage(
    ax: plt.Axes,
    x,
    y,
    *,
    color: str,
    xytext: tuple[float, float] = (0, 8),
    ha: str = "center",
    va: str = "bottom",
    overlap_points: set[tuple[float, float]] | None = None,
    overlap_xytext: tuple[float, float] | None = None,
    overlap_ha: str | None = None,
    overlap_va: str | None = None,
) -> None:
    for xi, yi in zip(x, y):
        point = (float(xi), float(yi))
        if overlap_points is not None and point in overlap_points and overlap_xytext is not None:
            offset = overlap_xytext
            align = overlap_ha or ha
            valign = overlap_va or va
        else:
            offset = xytext
            align = ha
            valign = va
        ax.annotate(
            _format_coverage_label(yi),
            (xi, yi),
            textcoords="offset points",
            xytext=offset,
            ha=align,
            va=valign,
            fontsize=7,
            color=color,
        )


def _overlapping_xy_points(df_a: pd.DataFrame, df_b: pd.DataFrame) -> set[tuple[float, float]]:
    """Return (x, y) points that appear in both series (same docks and coverage)."""
    points_a = {(float(x), float(y)) for x, y in zip(df_a["total"], df_a["coverage"])}
    points_b = {(float(x), float(y)) for x, y in zip(df_b["total"], df_b["coverage"])}
    return points_a & points_b


def _docks_budget_pairs(*dfs: pd.DataFrame) -> list[tuple[float, float]]:
    """
    Unique (docks_opened, budget) pairs for the secondary budget axis.

    When the same docks value maps to more than one budget across tables,
    keep the first occurrence after sorting by docks.
    """
    pairs: dict[float, float] = {}
    for df in dfs:
        for docks, budget in zip(df["total"], df["budget"]):
            docks_f = float(docks)
            if docks_f not in pairs:
                pairs[docks_f] = float(budget)
    return sorted(pairs.items(), key=lambda item: item[0])


def _add_budget_axis(
    ax: plt.Axes,
    docks_budget: list[tuple[float, float]],
    *,
    offset: float = BUDGET_AXIS_OFFSET,
) -> plt.Axes:
    """Add a second x-axis below docks opened, labeled with budget at each tick."""
    docks = [d for d, _ in docks_budget]
    budgets = [b for _, b in docks_budget]

    ax_budget = ax.twiny()
    ax_budget.set_xlim(ax.get_xlim())
    ax_budget.set_xticks(docks)
    ax_budget.set_xticklabels([_format_budget_label(b) for b in budgets])
    ax_budget.xaxis.set_ticks_position("bottom")
    ax_budget.xaxis.set_label_position("bottom")
    ax_budget.spines["top"].set_visible(False)
    ax_budget.spines["bottom"].set_position(("outward", offset))
    ax_budget.set_xlabel("Budget (docks)")
    return ax_budget


def _style_axes(
    ax: plt.Axes,
    *,
    title: str,
    xmax: float,
    ymax: float = 105,
) -> None:
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.set_xlabel("Docks opened")
    ax.set_ylabel("Incidents covered (%)")
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)


def _draw_docks_guides(ax: plt.Axes, docks: list[float]) -> None:
    for d in docks:
        ax.axvline(d, color="gray", linestyle="--", linewidth=0.9, alpha=0.35, zorder=0)


def _save_or_show(fig: plt.Figure, output_path: Path | str | None, show: bool) -> None:
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_docks_opened_vs_coverage(
    chart_df: pd.DataFrame,
    *,
    title: str = "Docks Opened vs Percentage of Incidents Covered",
    output_path: Path | str | None = DEFAULT_OUTPUT,
    show: bool = False,
) -> plt.Figure:
    x = chart_df["total"].to_numpy()
    y = chart_df["coverage"].to_numpy()
    docks_budget = _docks_budget_pairs(chart_df)

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    ax.plot(
        x,
        y,
        color=COVERAGE_LINE_COLOR,
        linewidth=2.5,
        marker="o",
        markersize=7,
        markerfacecolor=COVERAGE_LINE_COLOR,
        markeredgecolor="white",
        markeredgewidth=1.2,
        label="Incidents covered (%)",
        zorder=4,
    )
    _annotate_coverage(ax, x, y, color=COVERAGE_LINE_COLOR)

    xmax = float(chart_df["total"].max()) + 0.5
    _style_axes(ax, xmax=xmax, title=title)
    _draw_docks_guides(ax, [d for d, _ in docks_budget])
    _add_budget_axis(ax, docks_budget)

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=COVERAGE_LINE_COLOR,
            linewidth=2.5,
            marker="o",
            markersize=7,
            label="Incidents covered (%)",
        ),
    ]
    ax.legend(handles=legend_handles, loc="lower right", framealpha=0.95)
    fig.subplots_adjust(bottom=0.18)
    plt.tight_layout()

    _save_or_show(fig, output_path, show)
    return fig


# Backward-compatible alias.
plot_docks_opened_vs_budget = plot_docks_opened_vs_coverage


def plot_docks_opened_comparison(
    free_df: pd.DataFrame,
    preference_df: pd.DataFrame,
    *,
    title: str = "Docks Opened vs Percentage of Incidents Covered",
    output_path: Path | str | None = DEFAULT_COMPARISON_OUTPUT,
    show: bool = False,
) -> plt.Figure:
    """
    Line comparison chart for two side-by-side Excel tables.

    - Column A table  -> "Open docks freely"
    - Column G table  -> "Open MetroSafe docks first"
    """
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    overlap_points = _overlapping_xy_points(free_df, preference_df)
    docks_budget = _docks_budget_pairs(free_df, preference_df)

    series = [
        (
            free_df,
            COMPARISON_FREE_COLOR,
            "Open docks freely",
            7,
            (0, 10),
            "center",
            "bottom",
        ),
        (
            preference_df,
            COMPARISON_PREF_COLOR,
            "Open MetroSafe docks first",
            9,
            (0, -14),
            "center",
            "top",
        ),
    ]

    for df, color, label, markersize, overlap_xytext, overlap_ha, overlap_va in series:
        x = df["total"].to_numpy()
        y = df["coverage"].to_numpy()
        ax.plot(
            x,
            y,
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
        _annotate_coverage(
            ax,
            x,
            y,
            color=color,
            overlap_points=overlap_points,
            overlap_xytext=overlap_xytext,
            overlap_ha=overlap_ha,
            overlap_va=overlap_va,
        )

    all_docks = pd.concat([free_df["total"], preference_df["total"]], ignore_index=True)
    xmax = float(all_docks.max()) + 0.5
    _style_axes(ax, xmax=xmax, title=title)
    _draw_docks_guides(ax, [d for d, _ in docks_budget])
    _add_budget_axis(ax, docks_budget)

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=COMPARISON_FREE_COLOR,
            linewidth=2.5,
            marker="o",
            markersize=7,
            label="Open docks freely",
        ),
        Line2D(
            [0],
            [0],
            color=COMPARISON_PREF_COLOR,
            linewidth=3.0,
            marker="o",
            markersize=9,
            label="Open MetroSafe docks first",
        ),
    ]
    ax.legend(handles=legend_handles, loc="lower right", framealpha=0.95)
    fig.subplots_adjust(bottom=0.18)
    plt.tight_layout()

    _save_or_show(fig, output_path, show)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot Docks Opened vs % Incidents Covered from Excel."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input Excel file (default: {DEFAULT_INPUT.name})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output image path for the primary chart (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=DEFAULT_COMPARISON_OUTPUT,
        help=(
            "Output image path for the two-table comparison chart "
            f"(default: {DEFAULT_COMPARISON_OUTPUT})"
        ),
    )
    parser.add_argument("--show", action="store_true", help="Display the chart interactively.")
    args = parser.parse_args()

    primary_df, secondary_df = load_chart_tables(args.input)
    plot_docks_opened_vs_coverage(primary_df, output_path=args.output, show=args.show)
    print(f"Loaded {len(primary_df)} rows (primary table) from {args.input}")
    print(f"Chart saved to {args.output}")

    if secondary_df is not None:
        plot_docks_opened_comparison(
            primary_df,
            secondary_df,
            output_path=args.comparison_output,
            show=args.show,
        )
        print(f"Loaded {len(secondary_df)} rows (secondary table from column G)")
        print(f"Comparison chart saved to {args.comparison_output}")
    else:
        print("No second table detected at column G; skipped comparison chart.")


if __name__ == "__main__":
    main()
