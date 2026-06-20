from pathlib import Path

import folium
from src.docks_and_incidents import METROSAFE_DOCK_LOCATIONS, coverage

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

DOCK_COLOR = "#1f77b4"
METROSAFE_DOCK_BORDER_COLOR = "#1B5E20"
METROSAFE_DOCK_FILL_COLOR = "#A5D6A7"
INCIDENT_COVERED_COLOR = "#d62728"
INCIDENT_UNCOVERED_COLOR = "#6A1B9A"


def _dock_colors(dock):
    if dock.name in METROSAFE_DOCK_LOCATIONS:
        return METROSAFE_DOCK_BORDER_COLOR, METROSAFE_DOCK_FILL_COLOR
    return DOCK_COLOR, DOCK_COLOR


def _covered_incidents_set(docks, display_incidents, explicit_covered):
    if explicit_covered is not None:
        return set(explicit_covered)
    return {
        incident
        for incident in display_incidents
        if any(coverage(dock, incident) for dock in docks)
    }


def _add_incident_marker(map, incident, color):
    folium.CircleMarker(
        location=[incident.latitude, incident.longitude],
        radius=4,
        color=color,
        weight=1,
        fill=True,
        fill_color=color,
        fill_opacity=0.9,
        popup=folium.Popup(
            html=f"""
            <div style="padding-x:2px; white-space: nowrap;">
                {incident.incident_id}
            </div>
            """,
            max_width=100,
        ),
    ).add_to(map)


def create_map(docks, incidents, map_name, all_incidents=None, covered_incidents=None):
    try:
        map = folium.Map(
            location=[38.2527, -85.7585],
            zoom_start=12,
            tiles="CartoDB Positron",
        )

        display_incidents = all_incidents if all_incidents is not None else incidents
        explicit_covered = covered_incidents
        if explicit_covered is None and all_incidents is not None:
            explicit_covered = incidents
        covered_set = _covered_incidents_set(docks, display_incidents, explicit_covered)

        for incident in display_incidents:
            color = INCIDENT_COVERED_COLOR if incident in covered_set else INCIDENT_UNCOVERED_COLOR
            _add_incident_marker(map, incident, color)

        incidents_by_dock = {
            dock.name: sum(1 for incident in covered_set if coverage(dock, incident))
            for dock in docks
        }
        total_incidents = len(display_incidents)
        covered_count = len(covered_set)
        uncovered_incidents = total_incidents - covered_count
        covered_incidents_percentage = (covered_count / total_incidents * 100) if total_incidents else 0
        uncovered_incidents_percentage = (uncovered_incidents / total_incidents * 100) if total_incidents else 0

        for dock in docks:
            border_color, fill_color = _dock_colors(dock)
            folium.Circle(
                location=[dock.latitude, dock.longitude],
                radius=dock.effective_radius * 1609.344,  # convert miles to meters
                color=border_color,
                weight=1,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.10,
            ).add_to(map)

            folium.CircleMarker(
                location=[dock.latitude, dock.longitude],
                radius=3,
                color=border_color,
                fill=True,
                fill_color=border_color,
                fill_opacity=1,
                popup=folium.Popup(
                    html=f"""
                    <div style="padding-x:2px; white-space: nowrap;">
                        <b>{dock.name}</b><br>
                        Effective Radius: {dock.effective_radius:.2f} miles<br>
                        Covered Incidents: {incidents_by_dock[dock.name]}
                    </div>
                    """,
                    max_width=200,
                ),
            ).add_to(map)

        legend_html = f"""
        <div style="
            position: fixed;
            bottom: 25px;
            left: 25px;
            z-index: 1000;
            background-color: white;
            border: 2px solid #666;
            border-radius: 8px;
            padding: 10px 12px;
            font-size: 13px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            max-width: 320px;
        ">
            <div><b>Total Incidents:</b> {total_incidents}</div>
            <div><b>Dock Locations:</b> {len(docks)}</div>
            <div><b>Covered Incidents:</b> {covered_count} ({covered_incidents_percentage:.0f}%)</div>
            <div><b>Uncovered Incidents:</b> {uncovered_incidents} ({uncovered_incidents_percentage:.0f}%)</div>
            <div style="margin-top: 8px;">
                <span style="color:{INCIDENT_COVERED_COLOR};">&#9679;</span> Covered incident
                <span style="margin-left: 10px; color:{INCIDENT_UNCOVERED_COLOR};">&#9679;</span> Uncovered incident
            </div>
            <div>
                <span style="color:{DOCK_COLOR};">&#9679;</span> Dock
                <span style="margin-left: 10px; color:{METROSAFE_DOCK_BORDER_COLOR};">&#9679;</span> MetroSafe dock
            </div>
        </div>
        """
        map.get_root().html.add_child(folium.Element(legend_html))
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        map.save(str(OUTPUT_DIR / f"{map_name}.html"))
    except Exception as e:
        print(f"Error creating map: {e}")
