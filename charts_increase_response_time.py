"""
Generate Docks Opened vs Response Time chart from for_charts.xlsx.

Expected columns (header row):
  - Response time (min)
  - Coverage (%)
  - Total docks opened
  - Priority docks opened (or legacy: MetroSafe docks opened)
  - Other docks opened (or legacy: JCPS docks opened)

If a second table starts at column G, also generate a comparison line chart
(no bars) for both scenarios.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "tables_increase_response_time.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "figures" / "docks_opened_vs_response_time.png"
DEFAULT_COMPARISON_OUTPUT = (
    PROJECT_ROOT / "output" / "figures" / "docks_opened_vs_response_time_comparison.png"
)

TOTAL_LINE_COLOR = "#1a7f37"
METROSAFE_COLOR = "#4caf50"
JCPS_COLOR = "#1f77b4"
COVERAGE_LINE_COLOR = "#ff7f0e"
COMPARISON_FREE_COLOR = "#1a7f37"
COMPARISON_PREF_COLOR = "#ff7f0e"
FIG_SIZE = (12, 7)
BAR_WIDTH = 0.15

# Excel column G is 0-indexed column 6.
SECOND_TABLE_START_COL = 6

COLUMN_ALIASES = {
    "response_time": ["response time (min)", "response time", "response_time"],
    "coverage": ["coverage (%)", "coverage", "coverage_pct", "covered", "covered (%)"],
    "total": ["total docks opened", "total", "total_docks_opened"],
    "metrosafe": [
        "priority docks opened",
        "priority",
        "priority_docks_opened",
        "metrosafe docks opened",
        "metrosafe",
        "metrosafe_docks_opened",
    ],
    "jcps": [
        "other docks opened",
        "other",
        "other_docks_opened",
        "jcps docks opened",
        "jcps",
        "jcps_docks_opened",
    ],
}


def _normalize_column_name(name: object) -> str:
    return " ".join(str(name).strip().lower().replace("_", " ").split())


def _is_response_time_header(value: object) -> bool:
    return _normalize_column_name(value) in COLUMN_ALIASES["response_time"]


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
            "Expected columns such as 'Response time (min)' and 'Total docks opened'."
        )

    headers = [
        str(v).strip() if pd.notna(v) else f"col_{i}"
        for i, v in enumerate(block.iloc[header_row].tolist())
    ]
    df = block.iloc[header_row + 1 :].copy()
    df.columns = headers
    df = df.dropna(how="all")

    response_col = _resolve_column(df.columns.tolist(), "response_time")
    coverage_col = _resolve_column(df.columns.tolist(), "coverage")
    total_col = _resolve_column(df.columns.tolist(), "total")
    metrosafe_col = _resolve_column(df.columns.tolist(), "metrosafe")
    jcps_col = _resolve_column(df.columns.tolist(), "jcps")

    chart_df = pd.DataFrame(
        {
            "response_time": pd.to_numeric(df[response_col], errors="coerce"),
            "coverage": pd.to_numeric(df[coverage_col], errors="coerce"),
            "total": pd.to_numeric(df[total_col], errors="coerce"),
            "metrosafe": pd.to_numeric(df[metrosafe_col], errors="coerce"),
            "jcps": pd.to_numeric(df[jcps_col], errors="coerce"),
        }
    )
    chart_df = chart_df.dropna(subset=["response_time", "coverage", "total", "metrosafe", "jcps"])
    chart_df = chart_df.sort_values("response_time").reset_index(drop=True)

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
        if _is_response_time_header(first_cell):
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


def _y_axis_max(total_values: pd.Series, default_max: int = 12) -> int:
    data_max = int(total_values.max())
    if data_max <= default_max:
        return default_max
    return data_max + (1 if data_max % 2 == 0 else 0)


def _format_coverage_label(cov: float) -> str:
    return f"{cov:.2f}%"


def _annotate_coverage(ax: plt.Axes, x, y, coverage, color: str) -> None:
    for xi, yi, cov in zip(x, y, coverage):
        ax.annotate(
            _format_coverage_label(cov),
            (xi, yi),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=7,
            color=color,
        )


def _x_axis_max(response_times: pd.Series | list[float], padding: float = 0.5) -> float:
    """Axis upper bound from data, with a small pad so the last point is not flush."""
    return float(max(response_times)) + padding


def _style_axes(
    ax: plt.Axes,
    *,
    ymax: float,
    title: str,
    xmax: float,
) -> None:
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.set_xlabel("Response Time (min)")
    ax.set_ylabel("Docks Opened")
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)


def _save_or_show(fig: plt.Figure, output_path: Path | str | None, show: bool) -> None:
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_docks_opened_vs_response_time(
    chart_df: pd.DataFrame,
    *,
    title: str = "Docks Opened vs Response Time",
    output_path: Path | str | None = DEFAULT_OUTPUT,
    show: bool = False,
) -> plt.Figure:
    x = chart_df["response_time"].to_numpy()
    coverage = chart_df["coverage"].to_numpy()
    metrosafe = chart_df["metrosafe"].to_numpy()
    jcps = chart_df["jcps"].to_numpy()
    total = chart_df["total"].to_numpy()

    fig, ax = plt.subplots(figsize=FIG_SIZE)

    ax.bar(
        x,
        metrosafe,
        width=BAR_WIDTH,
        color=METROSAFE_COLOR,
        edgecolor="white",
        linewidth=0.8,
        label="Priority docks opened",
        zorder=2,
    )
    ax.bar(
        x,
        jcps,
        width=BAR_WIDTH,
        bottom=metrosafe,
        color=JCPS_COLOR,
        edgecolor="white",
        linewidth=0.8,
        label="Other docks opened",
        zorder=2,
    )
    ax.plot(
        x,
        total,
        color=TOTAL_LINE_COLOR,
        linewidth=2.5,
        marker="o",
        markersize=7,
        markerfacecolor=TOTAL_LINE_COLOR,
        markeredgecolor="white",
        markeredgewidth=1.2,
        label="Total docks opened",
        zorder=4,
    )
    _annotate_coverage(ax, x, total, coverage, COVERAGE_LINE_COLOR)

    _style_axes(
        ax,
        ymax=_y_axis_max(chart_df["total"]),
        xmax=_x_axis_max(chart_df["response_time"]),
        title=title,
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=TOTAL_LINE_COLOR,
            linewidth=2.5,
            marker="o",
            markersize=7,
            label="Total docks opened",
        ),
        Patch(facecolor=METROSAFE_COLOR, edgecolor="white", label="Priority docks opened"),
        Patch(facecolor=JCPS_COLOR, edgecolor="white", label="Other docks opened"),
        Line2D(
            [0],
            [0],
            linestyle="None",
            marker=None,
            color=COVERAGE_LINE_COLOR,
            label="Incidents covered (%)",
        ),
    ]
    legend = ax.legend(handles=legend_handles, loc="upper right", framealpha=0.95)
    legend.get_texts()[-1].set_color(COVERAGE_LINE_COLOR)
    plt.tight_layout()

    _save_or_show(fig, output_path, show)
    return fig


def plot_docks_opened_comparison(
    free_df: pd.DataFrame,
    preference_df: pd.DataFrame,
    *,
    title: str = "Docks Opened vs Response Time",
    output_path: Path | str | None = DEFAULT_COMPARISON_OUTPUT,
    show: bool = False,
) -> plt.Figure:
    """
    Line-only comparison chart for two side-by-side Excel tables.

    - Column A table  -> "Open docks freely"
    - Column G table  -> "Open priority docks first"
    """
    fig, ax = plt.subplots(figsize=FIG_SIZE)

    series = [
        (free_df, COMPARISON_FREE_COLOR, "Open docks freely", 7),
        (preference_df, COMPARISON_PREF_COLOR, "Open priority docks first", 9),
    ]

    for df, color, label, markersize in series:
        x = df["response_time"].to_numpy()
        y = df["total"].to_numpy()
        coverage = df["coverage"].to_numpy()
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
        _annotate_coverage(ax, x, y, coverage, color)

    all_totals = pd.concat([free_df["total"], preference_df["total"]], ignore_index=True)
    response_times = sorted(
        set(free_df["response_time"].tolist()) | set(preference_df["response_time"].tolist())
    )
    ymax = float(all_totals.max()) + 1
    _style_axes(ax, ymax=ymax, xmax=_x_axis_max(response_times), title=title)

    for rt in response_times:
        ax.axvline(rt, color="gray", linestyle="--", linewidth=0.9, alpha=0.35, zorder=0)

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
            label="Open priority docks first",
        ),
    ]
    ax.legend(handles=legend_handles, loc="upper right", framealpha=0.95)
    plt.tight_layout()

    _save_or_show(fig, output_path, show)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Docks Opened vs Response Time from Excel.")
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
    plot_docks_opened_vs_response_time(primary_df, output_path=args.output, show=args.show)
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
