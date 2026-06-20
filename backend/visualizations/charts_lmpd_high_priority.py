"""
LMPD and JCPS location visualizations.
Bar charts for LMPD incident distributions (month, hour, zip code) and JCPS schools by zip code.
Data sources:
  - output/clean_and_geocoded_LMPD_data_2025.xlsx
  - output/clean_and_geocoded_JCPS_schools.xlsx
"""
from __future__ import annotations
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_DATA_PATH = PROJECT_ROOT / "output" / "clean_and_geocoded_LMPD_data_2025.xlsx"
DEFAULT_JCPS_DATA_PATH = PROJECT_ROOT / "output" / "clean_and_geocoded_JCPS_schools.xlsx"
FIGURES_DIR = PROJECT_ROOT / "output" / "figures"

MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
BAR_COLOR = "#1f77b4"
CANDLE_BODY_COLOR = "#6baed6"
CANDLE_WICK_COLOR = "#2171b5"
CANDLE_MEAN_COLOR = "#d62728"
FIG_SIZE = (10, 6)
TOP_ZIPCODES = 10


def extract_zip_from_block_address(address: object) -> str | None:
    """Parse ZIP from ``"<street>, <city>, <zip>, <state>"``."""
    if pd.isna(address):
        return None
    parts = [part.strip() for part in str(address).split(",")]
    if len(parts) < 3:
        return None
    zip_part = parts[2] if len(parts) >= 4 else parts[-2]
    digits = "".join(ch for ch in zip_part if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return digits or None


def load_lmpd_data(data_path: Path | str = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load geocoded LMPD incidents and ensure datetime + zip_code columns."""
    path = Path(data_path)
    df = pd.read_excel(path)
    if "date_occurred" in df.columns:
        df["date_occurred"] = pd.to_datetime(df["date_occurred"], errors="coerce")
    elif {"date", "time"}.issubset(df.columns):
        df["date_occurred"] = pd.to_datetime(
            df["date"].astype(str) + " " + df["time"].astype(str),
            errors="coerce",
        )
    else:
        raise KeyError(f"Expected 'date_occurred' or ('date', 'time') in {path}")
    df = df.loc[df["date_occurred"].notna()].copy()

    if "block_address" in df.columns:
        df["zip_code"] = df["block_address"].map(extract_zip_from_block_address)

    if "priority" in df.columns:
        df = df.loc[df["priority"].notna()].copy()

    return df


def load_jcps_data(data_path: Path | str = DEFAULT_JCPS_DATA_PATH) -> pd.DataFrame:
    """Load geocoded JCPS schools and ensure ``zip_code`` is present."""
    path = Path(data_path)
    df = pd.read_excel(path)
    if "zip_code" not in df.columns:
        raise KeyError(f"Expected column 'zip_code' in {path}")
    df["zip_code"] = df["zip_code"].astype(str).str.strip()
    df = df.loc[df["zip_code"].notna() & (df["zip_code"] != "") & (df["zip_code"] != "nan")].copy()
    return df


def _counts_by_month(df: pd.DataFrame) -> pd.Series:
    counts = df["date_occurred"].dt.month.value_counts()
    return counts.reindex(range(1, 13), fill_value=0).astype(int)


def _daily_incidents_stats_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Min, max, and mean daily incident counts per calendar month."""
    daily = df.groupby(df["date_occurred"].dt.normalize()).size()
    stats = daily.groupby(daily.index.month).agg(["min", "max", "mean"])
    stats.columns = ["min", "max", "mean"]
    return stats.reindex(range(1, 13))


def _counts_by_hour(df: pd.DataFrame) -> pd.Series:
    counts = df["date_occurred"].dt.hour.value_counts()
    return counts.reindex(range(24), fill_value=0).astype(int)


def _counts_by_zipcode(df: pd.DataFrame, top_n: int = TOP_ZIPCODES) -> pd.Series:
    zips = df["zip_code"]
    counts = zips.value_counts(dropna=True)
    return counts.sort_values(ascending=False).head(top_n).astype(int)


def lmpd_top_zipcodes(df_lmpd: pd.DataFrame, top_n: int = TOP_ZIPCODES) -> list[str]:
    """Top LMPD zip codes by incident count, highest first (chart x-axis order)."""
    return [str(z) for z in _counts_by_zipcode(df_lmpd, top_n=top_n).index]


def _counts_for_zipcodes(df: pd.DataFrame, zipcodes: list[str]) -> pd.Series:
    """Count rows per zip, fixed order; missing zips are 0."""
    counts = df["zip_code"].astype(str).value_counts()
    return pd.Series(
        [int(counts.get(z, 0)) for z in zipcodes],
        index=zipcodes,
        dtype=int,
    )


def _y_axis_limit(max_count: float) -> tuple[float, float]:
    """Round ymax up to a sensible step (500 for large charts, smaller otherwise)."""
    max_count = int(max_count)
    if max_count <= 0:
        return 0.0, 10.0
    if max_count <= 50:
        step = 2
    elif max_count <= 400:
        step = 5
    else:
        step = 500
    ymax = ((max_count // step) + 1) * step
    return 0.0, float(ymax)


def plot_daily_incidents_candlestick(
    stats: pd.DataFrame,
    *,
    title: str,
    xlabel: str,
    x_tick_labels: list[str],
    ylabel: str = "Daily incidents",
    output_path: Path | str | None = None,
    show: bool = False,
) -> plt.Figure:
    """Candlestick chart: min/max daily range per month with mean marker."""
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    x_positions = range(len(x_tick_labels))
    candle_width = 0.45

    for x, month in zip(x_positions, stats.index):
        row = stats.loc[month]
        if pd.isna(row["min"]):
            continue

        low = float(row["min"])
        high = float(row["max"])
        mean = float(row["mean"])

        ax.vlines(
            x,
            low,
            high,
            color=CANDLE_WICK_COLOR,
            linewidth=2.2,
            zorder=2,
        )
        ax.bar(
            x,
            high - low,
            bottom=low,
            width=candle_width,
            color=CANDLE_BODY_COLOR,
            edgecolor=CANDLE_WICK_COLOR,
            linewidth=1.2,
            alpha=0.55,
            zorder=3,
        )
        ax.hlines(
            mean,
            x - candle_width / 2,
            x + candle_width / 2,
            color=CANDLE_MEAN_COLOR,
            linewidth=3.0,
            zorder=4,
        )
        ax.scatter(
            x,
            mean,
            color=CANDLE_MEAN_COLOR,
            s=28,
            zorder=5,
            edgecolors="white",
            linewidths=0.6,
        )

    valid_max = stats["max"].max()
    ymax = _y_axis_limit(float(valid_max) if pd.notna(valid_max) else 0)[1]
    step = 2 if ymax <= 20 else (5 if ymax <= 50 else 10)
    ax.set_ylim(0, ymax)
    ax.yaxis.set_major_locator(MultipleLocator(step))

    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(x_tick_labels, rotation=45, ha="right")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    legend_handles = [
        Patch(facecolor=CANDLE_BODY_COLOR, edgecolor=CANDLE_WICK_COLOR, alpha=0.55, label="Min–Max range"),
        Line2D([0], [0], color=CANDLE_MEAN_COLOR, linewidth=3, marker="o", markersize=5, label="Mean"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", framealpha=0.9)

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


def _annotate_bars(ax, bars, *, value_formatter=None) -> None:
    fmt = value_formatter or (lambda v: f"{int(v):,}")
    for bar in bars:
        height = bar.get_height()
        if height <= 0:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height * 0.97,
            fmt(height),
            ha="center",
            va="top",
            color="white",
            fontsize=9,
            fontweight="bold",
        )


def plot_incident_distribution(
    counts: pd.Series,
    *,
    title: str,
    xlabel: str,
    x_tick_labels: list[str] | None = None,
    rotate_xticks: float = 0,
    ylabel: str = "Total incidents",
    value_formatter=None,
    output_path: Path | str | None = None,
    show: bool = False,
) -> plt.Figure:
    """Vertical bar chart for count distributions."""
    labels = x_tick_labels if x_tick_labels is not None else [str(x) for x in counts.index]
    values = counts.values

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    bars = ax.bar(range(len(values)), values, color=BAR_COLOR, width=0.8)

    ymax = _y_axis_limit(int(values.max()))[1]
    ax.set_ylim(0, ymax)
    step = 500 if ymax >= 500 else (50 if ymax >= 100 else 10)
    ax.yaxis.set_major_locator(MultipleLocator(step))

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=rotate_xticks, ha="right" if rotate_xticks else "center")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    _annotate_bars(ax, bars, value_formatter=value_formatter)

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


def chart_distribution_by_month(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    show: bool = False,
) -> plt.Figure:
    counts = _counts_by_month(df)
    return plot_incident_distribution(
        counts,
        title="LMPD Incidents distribution by Month",
        xlabel="Month",
        x_tick_labels=MONTH_LABELS,
        rotate_xticks=45,
        output_path=output_path,
        show=show,
    )


def chart_daily_incidents_candlestick_by_month(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    show: bool = False,
) -> plt.Figure:
    stats = _daily_incidents_stats_by_month(df)
    return plot_daily_incidents_candlestick(
        stats,
        title="LMPD Daily Incidents by Month (Min, Max, Mean)",
        xlabel="Month",
        x_tick_labels=MONTH_LABELS,
        ylabel="Daily incidents",
        output_path=output_path,
        show=show,
    )


def chart_distribution_by_hour(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    show: bool = False,
) -> plt.Figure:
    counts = _counts_by_hour(df)
    return plot_incident_distribution(
        counts,
        title="LMPD Incidents distribution by Hours",
        xlabel="Hours",
        x_tick_labels=[str(h) for h in range(24)],
        output_path=output_path,
        show=show,
    )


def chart_distribution_by_zipcode(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    show: bool = False,
) -> plt.Figure:
    counts = _counts_by_zipcode(df)
    return plot_incident_distribution(
        counts,
        title=f"LMPD Incidents distribution by Zipcode (Top {TOP_ZIPCODES})",
        xlabel="Zipcode",
        x_tick_labels=[str(z) for z in counts.index],
        rotate_xticks=45,
        output_path=output_path,
        show=show,
    )


def chart_jcps_locations_by_zipcode(
    df: pd.DataFrame,
    zip_order: list[str],
    output_path: Path | str | None = None,
    show: bool = False,
) -> plt.Figure:
    """JCPS locations per zip, using the same zip codes and order as the LMPD chart."""
    counts = _counts_for_zipcodes(df, zip_order)
    n = len(zip_order)
    return plot_incident_distribution(
        counts,
        title=f"JCPS Locations distribution by Zipcode (LMPD Top {n})",
        xlabel="Zipcode",
        x_tick_labels=[str(z) for z in zip_order],
        rotate_xticks=45,
        ylabel="Total locations",
        output_path=output_path,
        show=show,
    )


def generate_all_charts(
    data_path: Path | str = DEFAULT_DATA_PATH,
    figures_dir: Path | str = FIGURES_DIR,
) -> dict[str, Path]:
    """Build and save month, hour, and zipcode distribution charts."""
    df = load_lmpd_data(data_path)
    out_dir = Path(figures_dir)

    paths = {
        "by_month": out_dir / "lmpd_distribution_by_month.png",
        "candlestick_by_month": out_dir / "lmpd_daily_incidents_candlestick_by_month.png",
        "by_hour": out_dir / "lmpd_distribution_by_hour.png",
        "by_zipcode": out_dir / "lmpd_distribution_by_zipcode.png",
    }

    chart_distribution_by_month(df, output_path=paths["by_month"])
    chart_daily_incidents_candlestick_by_month(df, output_path=paths["candlestick_by_month"])
    chart_distribution_by_hour(df, output_path=paths["by_hour"])
    chart_distribution_by_zipcode(df, output_path=paths["by_zipcode"])

    print(f"Loaded {len(df):,} incidents from {data_path}")
    for name, path in paths.items():
        print(f"  {name}: {path}")

    return paths


def generate_jcps_charts(
    data_path: Path | str = DEFAULT_JCPS_DATA_PATH,
    lmpd_data_path: Path | str = DEFAULT_DATA_PATH,
    figures_dir: Path | str = FIGURES_DIR,
) -> dict[str, Path]:
    """Build JCPS zip chart aligned to LMPD top zip codes (same order on x-axis)."""
    jcps_df = load_jcps_data(data_path)
    lmpd_df = load_lmpd_data(lmpd_data_path)
    zip_order = lmpd_top_zipcodes(lmpd_df)
    out_dir = Path(figures_dir)
    path = out_dir / "jcps_locations_by_zipcode.png"
    chart_jcps_locations_by_zipcode(jcps_df, zip_order, output_path=path)
    print(f"Loaded {len(jcps_df):,} JCPS locations from {data_path}")
    print(f"  Zip order from LMPD top {len(zip_order)}: {', '.join(zip_order)}")
    print(f"  by_zipcode: {path}")
    return {"by_zipcode": path}


if __name__ == "__main__":
    generate_all_charts()
    generate_jcps_charts()
