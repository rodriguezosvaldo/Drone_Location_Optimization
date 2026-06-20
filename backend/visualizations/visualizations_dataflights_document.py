"""
MetroSafe Flight Analysis - Chart generation for PDF report.
Generates bar charts and heatmaps for all statistics (matplotlib for PDF embedding).
"""
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for PDF generation
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis_dataflights_document import (
    get_agency_dock_crosstab,
    get_day_hour_crosstab,
    get_drone_utilization_by_dock,
    get_flights_by_location,
    get_incidents_by_agency,
    get_incidents_by_category,
    get_incidents_by_day,
    get_incidents_by_hour,
    load_and_prepare_data,
)

# Chart dimensions for PDF (inches)
CHART_WIDTH = 6.5
CHART_HEIGHT = 2.5
CHART_INCIDENTS_BY_DAY = (8.0, 4.0)  # Larger for Incidents by Day of Week
HEATMAP_HEIGHT = 4.0
HORIZONTAL_BAR_HEIGHT = 3.5
BAR_LABEL_FONTSIZE = 7


def _save_fig_to_temp(fig, prefix='chart'):
    """Save figure to temp file, return path. Caller should close fig."""
    import os
    fd, path = tempfile.mkstemp(suffix='.png', prefix=prefix)
    os.close(fd)
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    fig.clear()
    plt.close(fig)
    return path


def chart_incidents_by_day(df):
    """Bar chart: Incidents by Day of Week (larger size)."""
    data = get_incidents_by_day(df)
    w, h = CHART_INCIDENTS_BY_DAY
    fig, ax = plt.subplots(figsize=(w, h))
    bars = ax.bar(data.index.astype(str), data.values, color='steelblue', edgecolor='navy', alpha=0.8)
    ax.bar_label(bars, fontsize=BAR_LABEL_FONTSIZE, padding=2)
    ax.set_xlabel('Day of Week')
    ax.set_ylabel('Incidents')
    ax.set_title('A. Incidents by Day of Week')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'incidents_day')
    return path


def chart_incidents_by_hour(df):
    """Horizontal bar chart: Incidents by Hour of Day (matches table - only hours with incidents)."""
    data = get_incidents_by_hour(df)
    # Same as table: only hours that have incidents, in chronological order
    hours = sorted(data.index.tolist())
    values = [data[h] for h in hours]
    labels = [f'{h:02d}:00-{h:02d}:59' for h in hours]
    n = len(hours)
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, max(HORIZONTAL_BAR_HEIGHT, n * 0.4)))
    y_pos = np.arange(n)
    bars = ax.barh(y_pos, values, color='steelblue', edgecolor='navy', alpha=0.8)
    ax.bar_label(bars, fontsize=BAR_LABEL_FONTSIZE, padding=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel('Incidents')
    ax.set_ylabel('Hour of Day')
    ax.set_title('B. Incidents by Hour of Day')
    ax.invert_yaxis()
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'incidents_hour')
    return path


def chart_incidents_by_category(df):
    """Horizontal bar chart: Incidents by Category (better for long labels)."""
    data = get_incidents_by_category(df)
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, max(HORIZONTAL_BAR_HEIGHT, len(data) * 0.35)))
    y_pos = np.arange(len(data))
    bars = ax.barh(y_pos, data.values, color='steelblue', edgecolor='navy', alpha=0.8)
    ax.bar_label(bars, fontsize=BAR_LABEL_FONTSIZE, padding=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([str(s)[:40] + ('...' if len(str(s)) > 40 else '') for s in data.index])
    ax.set_xlabel('Incidents')
    ax.set_ylabel('Category')
    ax.set_title('D. Incidents by Category')
    ax.invert_yaxis()
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'incidents_cat')
    return path


def chart_day_hour_heatmap(df):
    """Heatmap: Incident frequency by Day and Hour."""
    ct = get_day_hour_crosstab(df)
    if 'TOTAL' in ct.columns:
        plot_data = ct.drop(columns=['TOTAL'])
    else:
        plot_data = ct
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, HEATMAP_HEIGHT))
    im = ax.imshow(plot_data.values, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(np.arange(plot_data.shape[1]))
    ax.set_yticks(np.arange(plot_data.shape[0]))
    ax.set_xticklabels([str(int(h)) for h in plot_data.columns])
    ax.set_yticklabels(plot_data.index.astype(str))
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Day of Week')
    ax.set_title('C. Incident Frequency by Day and Hour')
    plt.colorbar(im, ax=ax, label='Incidents')
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'heatmap')
    return path


def _shorten_address(addr, max_len=35):
    """Shorten address for chart labels."""
    s = str(addr)
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + '...'


def chart_drone_utilization(df):
    """Heatmap: Drone utilization by dock (docks x drones, count = takeoffs)."""
    ct = get_drone_utilization_by_dock(df)
    if 'TOTAL' in ct.columns:
        plot_data = ct.drop(columns=['TOTAL'])
    else:
        plot_data = ct
    n_docks, n_drones = plot_data.shape
    fig_h = max(HEATMAP_HEIGHT, n_docks * 0.45)
    fig_w = max(CHART_WIDTH, n_drones * 0.9)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(plot_data.values, cmap='Blues', aspect='auto')
    ax.set_xticks(np.arange(n_drones))
    ax.set_yticks(np.arange(n_docks))
    ax.set_xticklabels([str(c).replace('SkydioX10-', '') for c in plot_data.columns])
    ax.set_yticklabels([_shorten_address(r) for r in plot_data.index], fontsize=8)
    ax.set_xlabel('Drone')
    ax.set_ylabel('Dock Location')
    ax.set_title('Drone Utilization by Dock')
    for i in range(n_docks):
        for j in range(n_drones):
            val = plot_data.iloc[i, j]
            if val > 0:
                ax.text(j, i, int(val), ha='center', va='center', fontsize=7, color='white' if val > plot_data.values.max() / 2 else 'black')
    plt.colorbar(im, ax=ax, label='Takeoffs')
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'drone_util')
    return path


def chart_flights_by_location(df):
    """Horizontal bar chart: Flights by Dock Location."""
    data = get_flights_by_location(df)
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, max(HORIZONTAL_BAR_HEIGHT, len(data) * 0.4)))
    y_pos = np.arange(len(data))
    bars = ax.barh(y_pos, data.values, color='forestgreen', edgecolor='darkgreen', alpha=0.8)
    ax.bar_label(bars, fontsize=BAR_LABEL_FONTSIZE, padding=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([str(s)[:50] + ('...' if len(str(s)) > 50 else '') for s in data.index], fontsize=8)
    ax.set_xlabel('Number of Flights')
    ax.set_ylabel('Dock Location')
    ax.set_title('Flights by Dock Location')
    ax.invert_yaxis()
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'flights_loc')
    return path


def chart_incidents_by_agency(df):
    """Horizontal bar chart: Incidents by Responding Agency."""
    data = get_incidents_by_agency(df)
    n = len(data)
    fig, ax = plt.subplots(figsize=(CHART_WIDTH, max(HORIZONTAL_BAR_HEIGHT, n * 0.35)))
    y_pos = np.arange(n)
    bars = ax.barh(y_pos, data.values, color='darkorange', edgecolor='saddlebrown', alpha=0.8)
    ax.bar_label(bars, fontsize=BAR_LABEL_FONTSIZE, padding=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([str(s)[:50] + ('...' if len(str(s)) > 50 else '') for s in data.index], fontsize=8)
    ax.set_xlabel('Incidents')
    ax.set_ylabel('Agencies')
    ax.set_title('E. Incidents by Responding Agency')
    ax.invert_yaxis()
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'incidents_agency')
    return path


def chart_agency_dock_heatmap(df):
    """Heatmap: Agency-related incidents by dock location (docks x agencies)."""
    ct = get_agency_dock_crosstab(df)
    if ct.empty:
        return None
    if 'TOTAL' in ct.columns:
        plot_data = ct.drop(columns=['TOTAL'])
    else:
        plot_data = ct
    n_docks, n_agencies = plot_data.shape
    fig_h = max(HEATMAP_HEIGHT, n_docks * 0.45)
    fig_w = max(CHART_WIDTH, n_agencies * 1.1)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(plot_data.values, cmap='Oranges', aspect='auto')
    ax.set_xticks(np.arange(n_agencies))
    ax.set_yticks(np.arange(n_docks))
    ax.set_xticklabels(plot_data.columns, rotation=30, ha='right', fontsize=8)
    ax.set_yticklabels([_shorten_address(r) for r in plot_data.index], fontsize=8)
    ax.set_xlabel('Agencies')
    ax.set_ylabel('Dock Location')
    ax.set_title('Agency-Related Incidents by Dock Location')
    for i in range(n_docks):
        for j in range(n_agencies):
            val = plot_data.iloc[i, j]
            if val > 0:
                ax.text(j, i, int(val), ha='center', va='center', fontsize=7,
                        color='white' if val > plot_data.values.max() / 2 else 'black')
    plt.colorbar(im, ax=ax, label='Incidents')
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'agency_dock')
    return path


def chart_agency_dock_heatmap_pct(df):
    """Heatmap: Agency-related incidents as % of total incidents per dock."""
    ct = get_agency_dock_crosstab(df)
    if ct.empty:
        return None
    if 'TOTAL' in ct.columns:
        totals = ct['TOTAL']
        plot_data = ct.drop(columns=['TOTAL'])
    else:
        totals = ct.sum(axis=1)
        plot_data = ct
    # Compute row-wise percentages (% of each dock's total)
    pct_data = plot_data.div(totals, axis=0).mul(100)
    n_docks, n_agencies = pct_data.shape
    fig_h = max(HEATMAP_HEIGHT, n_docks * 0.45)
    fig_w = max(CHART_WIDTH, n_agencies * 1.1)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(pct_data.values, cmap='Oranges', aspect='auto', vmin=0, vmax=100)
    ax.set_xticks(np.arange(n_agencies))
    ax.set_yticks(np.arange(n_docks))
    ax.set_xticklabels(pct_data.columns, rotation=30, ha='right', fontsize=8)
    ax.set_yticklabels([_shorten_address(r) for r in pct_data.index], fontsize=8)
    ax.set_xlabel('Agencies')
    ax.set_ylabel('Dock Location')
    ax.set_title('Agency-Related Incidents by Dock Location (% of Dock Total)')
    for i in range(n_docks):
        for j in range(n_agencies):
            val = pct_data.iloc[i, j]
            if val > 0:
                ax.text(j, i, f'{val:.1f}%', ha='center', va='center', fontsize=7,
                        color='white' if val > 50 else 'black')
    plt.colorbar(im, ax=ax, label='% of Dock Incidents')
    plt.tight_layout()
    path = _save_fig_to_temp(fig, 'agency_dock_pct')
    return path


def generate_all_charts(df):
    """Generate all charts and return list of (label, temp_path) for PDF insertion."""
    charts = []
    try:
        charts.append(('incidents_by_day', chart_incidents_by_day(df)))
        charts.append(('incidents_by_hour', chart_incidents_by_hour(df)))
        charts.append(('day_hour_heatmap', chart_day_hour_heatmap(df)))
        charts.append(('incidents_by_category', chart_incidents_by_category(df)))
        charts.append(('incidents_by_agency', chart_incidents_by_agency(df)))
        agency_dock_path = chart_agency_dock_heatmap(df)
        if agency_dock_path:
            charts.append(('agency_dock_heatmap', agency_dock_path))
        agency_dock_pct_path = chart_agency_dock_heatmap_pct(df)
        if agency_dock_pct_path:
            charts.append(('agency_dock_heatmap_pct', agency_dock_pct_path))
        charts.append(('flights_by_location', chart_flights_by_location(df)))
        charts.append(('drone_utilization', chart_drone_utilization(df)))
    except Exception:
        # Clean up any temp files on error
        for _, p in charts:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass
        raise
    return charts


def cleanup_chart_files(chart_paths):
    """Remove temporary chart files."""
    for path in chart_paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass
