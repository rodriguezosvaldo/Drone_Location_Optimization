import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import warnings
import sys
from io import StringIO
from fpdf import FPDF
warnings.filterwarnings('ignore')

# Default data path (CSV in project root)
DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_DATA_PATH = PROJECT_ROOT / 'data' / 'Dataflights.csv'


def load_and_prepare_data(csv_path=None):
    """Load CSV and prepare columns for analysis. Returns prepared DataFrame."""
    path = Path(csv_path) if csv_path else DEFAULT_DATA_PATH
    df = pd.read_csv(path)
    df['Local Takeoff Time'] = pd.to_datetime(df['Local Takeoff Time'], errors='coerce')
    df['Takeoff'] = pd.to_datetime(df['Takeoff'], errors='coerce')
    df['Land'] = pd.to_datetime(df['Land'], errors='coerce')
    df['Day'] = pd.Categorical(df['Local Takeoff Time'].dt.day_name(), categories=DAY_ORDER, ordered=True)
    df['Hour'] = df['Local Takeoff Time'].dt.hour
    df['Date'] = df['Local Takeoff Time'].dt.date
    df['Type of incident'] = df['Type of incident'].fillna('Blank/Not Specified')
    df['Type of incident'] = df['Type of incident'].apply(lambda x: 'Blank/Not Specified' if str(x).strip() == '' else x)
    return df


def get_incidents_by_day(df):
    """Return incidents count per day of week (ordered Monday-Sunday)."""
    incidents = df['Day'].value_counts().sort_values(ascending=False)
    return incidents.reindex([d for d in DAY_ORDER if d in incidents.index])


def get_incidents_by_hour(df):
    """Return incidents count per hour of day."""
    return df['Hour'].value_counts().sort_index()


_NON_OPERATIONAL_LABEL = 'Non-operational (i.e. training flight)'

# Case-insensitive exact values that collapse into the non-operational category
_NON_OPERATIONAL_EXACT = {
    'non-operational (i.e. training flight)',
    'test',
    'testing',
    'training',
    'training flight',
    'test flight',
}


_SEARCH_RESCUE_LABEL = 'Search & rescue'

# Exact values (case-insensitive, stripped) that collapse into Search & rescue
_SEARCH_RESCUE_EXACT = {
    'search & rescue',
    'search & rescue, dispatch call for service',
    'dispatch call for service, search & rescue',
}


def _normalize_incident_category(val):
    """Merge training/test and search & rescue variants into canonical categories."""
    s = str(val).strip()
    sl = s.lower().replace('\r', '').replace('\n', ' ').strip()
    # Non-operational merges
    if sl in _NON_OPERATIONAL_EXACT:
        return _NON_OPERATIONAL_LABEL
    if sl.startswith('non-operational'):
        return _NON_OPERATIONAL_LABEL
    # Search & rescue merges
    if sl in _SEARCH_RESCUE_EXACT:
        return _SEARCH_RESCUE_LABEL
    return s


def get_incidents_by_category(df):
    """Return incidents count per category, with training/test variants merged."""
    normalized = df['Type of incident'].apply(_normalize_incident_category)
    return normalized.value_counts()


def get_day_hour_crosstab(df):
    """Return crosstab of incidents by day and hour."""
    ct = pd.crosstab(df['Day'], df['Hour'])
    ct['TOTAL'] = ct.sum(axis=1)
    return ct


def get_flights_by_location(df):
    """Return flights count per dock location."""
    return df['Takeoff Address'].value_counts()


def get_drone_utilization_by_dock(df):
    """Return crosstab: dock (rows) x drone/vehicle (columns), values = takeoff count."""
    ct = pd.crosstab(df['Takeoff Address'], df['Vehicle'])
    ct['TOTAL'] = ct.sum(axis=1)
    return ct


AGENCY_COL = 'Which agencies responded to this incident?'
INCIDENT_ID_COL = 'Incident ID'


def _infer_agency_from_incident_id(incident_id):
    """Infer agency from Incident ID prefix when the agency field is blank.
    Returns 'Fire' for LFD-prefixed IDs, 'Police' for LMPD-prefixed IDs,
    or None if the prefix is not recognized."""
    if pd.isna(incident_id):
        return None
    iid = str(incident_id).strip()
    if iid.startswith('LFD'):
        return 'Fire'
    if iid.startswith('LMPD'):
        return 'Police'
    return None


def _get_row_agency(row):
    """Return the normalized agency label for a single row.
    If the agency field is blank, falls back to Incident ID prefix inference.
    Multi-agency combos are sorted alphabetically to merge order variants."""
    val = row[AGENCY_COL]
    if pd.isna(val) or str(val).strip() == '':
        inferred = _infer_agency_from_incident_id(row.get(INCIDENT_ID_COL))
        return inferred if inferred else 'Blank/Not Specified'
    parts = sorted([a.strip() for a in str(val).split(',')])
    return ', '.join(parts)


def get_incidents_by_agency(df):
    """Return incidents count per normalized responding agency, sorted descending."""
    normalized = df.apply(_get_row_agency, axis=1)
    return normalized.value_counts()


def get_agency_dock_crosstab(df):
    """Return crosstab: dock (rows) x normalized agency category (columns).
    Uses the same normalized categories as get_incidents_by_agency so both
    the bar chart and heatmap share identical category labels."""
    normalized = df.apply(_get_row_agency, axis=1)
    ct = pd.crosstab(df['Takeoff Address'], normalized)
    ct['TOTAL'] = ct.sum(axis=1)
    return ct


def run_report(output_buffer, add_chart_markers=False, df=None, title=None):
    """Generate the full text report into the given buffer. Returns prepared df.
    If add_chart_markers=True, inserts [CHART:key] lines for PDF chart embedding.
    If df is provided, use it instead of loading (allows pre-filtered data).
    If title is provided, use it for the report header."""
    if df is None:
        df = load_and_prepare_data()
    m = add_chart_markers
    report_title = title or "METROSAFE FLIGHT ANALYSIS - SUMMARY STATISTICS"

    print("=" * 80, file=output_buffer)
    print(report_title, file=output_buffer)
    print("=" * 80, file=output_buffer)
    print(file=output_buffer)

    # TABLE 1
    print("1. NUMBER OF INCIDENTS BY DAY, HOUR, AND INCIDENT CATEGORY", file=output_buffer)
    print("-" * 80, file=output_buffer)

    print("\nA. INCIDENTS BY DAY OF WEEK", file=output_buffer)
    incidents_by_day = get_incidents_by_day(df)
    for day, count in incidents_by_day.items():
        print(f"  {day:12s}: {count:3d} incidents", file=output_buffer)
    print(f"  {'Total':12s}: {incidents_by_day.sum():3d} incidents", file=output_buffer)
    if m:
        print("[CHART:incidents_by_day]", file=output_buffer)

    if m:
        print("[NEWPAGE]", file=output_buffer)
    print("\nB. INCIDENTS BY HOUR OF DAY", file=output_buffer)
    incidents_by_hour = get_incidents_by_hour(df)
    total_by_hour = 0
    for hour in range(24):
        if hour in incidents_by_hour.index:
            count = incidents_by_hour[hour]
            print(f"  {hour:02d}:00-{hour:02d}:59: {count:3d} incidents", file=output_buffer)
            total_by_hour += count
    print(f"  {'Total':10s}: {total_by_hour:3d} incidents", file=output_buffer)
    if m:
        print("[CHART:incidents_by_hour]", file=output_buffer)

    if m:
        print("[NEWPAGE]", file=output_buffer)
    print("\nC. INCIDENT FREQUENCY BY DAY AND HOUR (Selected Hours)", file=output_buffer)
    day_hour_crosstab = get_day_hour_crosstab(df)
    print(day_hour_crosstab.to_string(), file=output_buffer)
    print(f"\nTOTAL: {day_hour_crosstab['TOTAL'].sum():d} incidents", file=output_buffer)
    if m:
        print("[CHART:day_hour_heatmap]", file=output_buffer)

    if m:
        print("[NEWPAGE]", file=output_buffer)
    print("\nD. INCIDENTS BY CATEGORY", file=output_buffer)
    incidents_by_category = get_incidents_by_category(df)
    for category, count in incidents_by_category.items():
        print(f"  {category:50s}: {count:3d} incidents", file=output_buffer)
    print(f"  {'Total':50s}: {incidents_by_category.sum():3d} incidents", file=output_buffer)

    print("\nE. INCIDENTS BY RESPONDING AGENCY", file=output_buffer)
    incidents_by_agency = get_incidents_by_agency(df)
    for agency, count in incidents_by_agency.items():
        print(f"  {str(agency):50s}: {count:3d} incidents", file=output_buffer)
    print(f"  {'Total':50s}: {incidents_by_agency.sum():3d} incidents", file=output_buffer)
    if m:
        print("[CHART:incidents_by_category]", file=output_buffer)
        print("[CHART:incidents_by_agency]", file=output_buffer)
        print("[CHART:agency_dock_heatmap]", file=output_buffer)
        print("[CHART:agency_dock_heatmap_pct]", file=output_buffer)
    print(file=output_buffer)

    if m:
        print("[NEWPAGE]", file=output_buffer)
    # TABLE 2
    print("2. NUMBER OF FLIGHTS BY DOCK LOCATION", file=output_buffer)
    print("-" * 80, file=output_buffer)
    flights_by_location = get_flights_by_location(df)
    print(file=output_buffer)
    for location, count in flights_by_location.items():
        print(f"  {location:60s}: {count:3d} flights", file=output_buffer)
    print(f"  {'Total':60s}: {len(df):3d} flights", file=output_buffer)
    if m:
        print("[CHART:flights_by_location]", file=output_buffer)
    print(file=output_buffer)

    if m:
        print("[NEWPAGE]", file=output_buffer)
    print("3. DRONE UTILIZATION BY DOCK", file=output_buffer)
    print("-" * 80, file=output_buffer)
    if m:
        print("[CHART:drone_utilization]", file=output_buffer)
    print(file=output_buffer)

    return df


def _generate_pdf(output_text, chart_paths=None, pdf_filename='MetroSafe_Analysis_Report.pdf', title=None):
    """Generate PDF report from text output. chart_paths: dict of key -> png path for embedding."""
    chart_paths = chart_paths or {}
    if title is None:
        title = "MetroSafe Flight Analysis - Summary Statistics"

    class PDFWithPageBreaks(FPDF):
        def __init__(self, header_title):
            super().__init__()
            self.set_auto_page_break(auto=True, margin=10)
            self.header_title = header_title

        def header(self):
            if self.page == 1:
                self.set_font("Helvetica", "B", 14)
                self.cell(0, 10, self.header_title, 0, 1, "C")
                self.ln(5)

    pdf = PDFWithPageBreaks(title)

    pdf.add_page()
    pdf.set_font("Courier", "", 9)

    for line in output_text.split('\n'):
        line_stripped = line.strip()
        if line_stripped == '[NEWPAGE]':
            pdf.add_page()
            continue
        if line_stripped.startswith('[CHART:') and line_stripped.endswith(']'):
            key = line_stripped[7:-1]
            if key in chart_paths:
                img_path = chart_paths[key]
                try:
                    pdf.ln(3)
                    pdf.image(img_path, w=180)  # 180mm width for A4 page
                    pdf.ln(3)
                except Exception:
                    pass
            continue

        if len(line) > 100:
            while len(line) > 100:
                pdf.cell(0, 4, line[:100], 0, 1)
                line = line[100:]
            if line:
                pdf.cell(0, 4, line, 0, 1)
        else:
            pdf.cell(0, 4, line, 0, 1)

    pdf.output(pdf_filename)
    return pdf_filename


if __name__ == '__main__':
    from visualizations.visualizations_dataflights_document import (
        generate_all_charts,
        cleanup_chart_files,
    )

    output_buffer = StringIO()
    original_stdout = sys.stdout
    sys.stdout = output_buffer

    df = run_report(output_buffer, add_chart_markers=True)

    sys.stdout = original_stdout
    output_text = output_buffer.getvalue()

    charts = generate_all_charts(df)
    chart_paths = {key: path for key, path in charts}

    output_dir = PROJECT_ROOT / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / 'MetroSafe_Analysis_Report.pdf'
    _generate_pdf(output_text, chart_paths, str(pdf_path))

    cleanup_chart_files([p for _, p in charts])
    print("Report successfully generated.")
