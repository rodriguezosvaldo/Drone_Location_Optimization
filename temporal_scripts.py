"""
Generate Docks Opened vs Response Time chart from for_charts.xlsx.

Expected columns (header row):
  - Response time (min)
  - Coverage (%)
  - Total docks opened
  - MetroSafe docks opened
  - JCPS docks opened
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
DEFAULT_INPUT = PROJECT_ROOT / "for_charts.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "figures" / "docks_opened_vs_response_time.png"

TOTAL_LINE_COLOR = "#1a7f37"
METROSAFE_COLOR = "#4caf50"
JCPS_COLOR = "#1f77b4"
COVERAGE_LINE_COLOR = "#ff7f0e"
FIG_SIZE = (12, 7)
BAR_WIDTH = 0.15

COLUMN_ALIASES = {
    "response_time": ["response time (min)", "response time", "response_time"],
    "coverage": ["coverage (%)", "coverage", "coverage_pct", "covered", "covered (%)"],
    "total": ["total docks opened", "total", "total_docks_opened"],
    "metrosafe": ["metrosafe docks opened", "metrosafe", "metrosafe_docks_opened"],
    "jcps": ["jcps docks opened", "jcps", "jcps_docks_opened"],
}


def _normalize_column_name(name: object) -> str:
    return " ".join(str(name).strip().lower().replace("_", " ").split())


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


def load_chart_data(input_path: Path | str = DEFAULT_INPUT) -> pd.DataFrame:
    path = Path(input_path)
    raw = pd.read_excel(path, header=None)
    if raw.empty:
        raise ValueError(f"No data found in {path}")

    header_row = _find_header_row(raw)
    if header_row is None:
        raise ValueError(
            f"Could not find a header row in {path}. "
            "Expected columns such as 'Response time (min)' and 'Total docks opened'."
        )

    df = pd.read_excel(path, header=header_row)
    df = df.dropna(how="all").copy()

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
        raise ValueError(f"No valid numeric rows found in {path}")

    return chart_df


def _y_axis_max(total_values: pd.Series, default_max: int = 12) -> int:
    data_max = int(total_values.max())
    if data_max <= default_max:
        return default_max
    return data_max + (1 if data_max % 2 == 0 else 0)


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
        label="MetroSafe docks opened",
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
        label="JCPS docks opened",
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
    for xi, yi, cov in zip(x, total, coverage):
        label = f"{cov:.0f}%" if cov == int(cov) else f"{cov:.1f}%"
        ax.annotate(
            label,
            (xi, yi),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=7,
            color=COVERAGE_LINE_COLOR,
        )

    ymax = _y_axis_max(chart_df["total"])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, ymax)
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.set_xlabel("Response Time (min)")
    ax.set_ylabel("Docks Opened")
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

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
        Patch(facecolor=METROSAFE_COLOR, edgecolor="white", label="MetroSafe docks opened"),
        Patch(facecolor=JCPS_COLOR, edgecolor="white", label="JCPS docks opened"),
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

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")

    if show:
        plt.show()
    else:
        plt.close(fig)

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
        help=f"Output image path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--show", action="store_true", help="Display the chart interactively.")
    args = parser.parse_args()

    chart_df = load_chart_data(args.input)
    plot_docks_opened_vs_response_time(chart_df, output_path=args.output, show=args.show)
    print(f"Loaded {len(chart_df)} rows from {args.input}")
    print(f"Chart saved to {args.output}")


if __name__ == "__main__":
    main()
