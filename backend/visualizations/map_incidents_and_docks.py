from pathlib import Path
import folium

BACKEND_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BACKEND_ROOT.parent / "output"

DOCK_COLOR = "#1f77b4"
PRIORITY_DOCK_BORDER_COLOR = "#1B5E20"
PRIORITY_DOCK_FILL_COLOR = "#A5D6A7"
INCIDENT_COVERED_COLOR = "#d62728"
INCIDENT_UNCOVERED_COLOR = "#6A1B9A"
BOUNDARY_LINE_COLOR = "#E65100"


def _dock_colors(dock, priority_dock_names):
    if dock.name in priority_dock_names:
        return PRIORITY_DOCK_BORDER_COLOR, PRIORITY_DOCK_FILL_COLOR
    return DOCK_COLOR, DOCK_COLOR

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

def _add_area_boundary_lines(
    map,
    latitude_closest_to_ecuador,
    latitude_farthest_from_ecuador,
    longitude_closest_to_greenwich,
    longitude_farthest_from_greenwich,
):
    line_style = dict(color=BOUNDARY_LINE_COLOR, weight=2, dash_array="8, 6")

    folium.PolyLine(
        locations=[
            [latitude_closest_to_ecuador, longitude_closest_to_greenwich],
            [latitude_closest_to_ecuador, longitude_farthest_from_greenwich],
        ],
        popup=folium.Popup(f"{latitude_closest_to_ecuador:.6f}", max_width=150),
        tooltip=f"{latitude_closest_to_ecuador:.6f}",
        **line_style,
    ).add_to(map)

    folium.PolyLine(
        locations=[
            [latitude_farthest_from_ecuador, longitude_closest_to_greenwich],
            [latitude_farthest_from_ecuador, longitude_farthest_from_greenwich],
        ],
        popup=folium.Popup(f"{latitude_farthest_from_ecuador:.6f}", max_width=150),
        tooltip=f"{latitude_farthest_from_ecuador:.6f}",
        **line_style,
    ).add_to(map)

    folium.PolyLine(
        locations=[
            [latitude_closest_to_ecuador, longitude_closest_to_greenwich],
            [latitude_farthest_from_ecuador, longitude_closest_to_greenwich],
        ],
        popup=folium.Popup(f"{longitude_closest_to_greenwich:.6f}", max_width=150),
        tooltip=f"{longitude_closest_to_greenwich:.6f}",
        **line_style,
    ).add_to(map)

    folium.PolyLine(
        locations=[
            [latitude_closest_to_ecuador, longitude_farthest_from_greenwich],
            [latitude_farthest_from_ecuador, longitude_farthest_from_greenwich],
        ],
        popup=folium.Popup(f"{longitude_farthest_from_greenwich:.6f}", max_width=150),
        tooltip=f"{longitude_farthest_from_greenwich:.6f}",
        **line_style,
    ).add_to(map)

def create_map(
    priority_dock_names=None,
    docks=None,
    incidents=None,
    map_name="map",
    incidents_covered=None,
    dock_assignments=None,
    latitude_closest_to_ecuador=None,
    latitude_farthest_from_ecuador=None,
    longitude_closest_to_greenwich=None,
    longitude_farthest_from_greenwich=None,
):
    print(f"Creating map: {map_name}...")
    try:
        has_area_bounds = all(
            value is not None
            for value in (
                latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich,
            )
        )
        if incidents:
            incident_latitude_mean = sum(incident.latitude for incident in incidents) / len(incidents)
            incident_longitude_mean = sum(incident.longitude for incident in incidents) / len(incidents)
        else:
            incident_latitude_mean = 0
            incident_longitude_mean = 0

        map = folium.Map(
            location=[incident_latitude_mean, incident_longitude_mean],
            zoom_start=11,
            tiles="CartoDB Positron",
        )

        if has_area_bounds:
            _add_area_boundary_lines(
                map,
                latitude_closest_to_ecuador,
                latitude_farthest_from_ecuador,
                longitude_closest_to_greenwich,
                longitude_farthest_from_greenwich,
            )

        uncovered_incidents = [incident for incident in incidents if incident not in incidents_covered]

        for incident in uncovered_incidents:
            _add_incident_marker(map, incident, INCIDENT_UNCOVERED_COLOR)

        for incident in incidents_covered:
            _add_incident_marker(map, incident, INCIDENT_COVERED_COLOR)

        for dock in docks:
            dock_radius = dock.effective_radius*1609.34 # convert miles to meters to be able to use the folium library
            if dock_assignments is not None:
                covered_incidents = dock_assignments.get(dock, [])
            else:
                covered_incidents, _ = dock.incidents_covered(incidents_covered)
            border_color, fill_color = _dock_colors(dock, priority_dock_names)
            folium.Circle(
                location=[dock.latitude, dock.longitude],
                radius=dock_radius,
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
                        Covered Incidents: {len(covered_incidents)}
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
            <div><b>Total Incidents:</b> {len(incidents)}</div>
            <div><b>Dock Locations:</b> {len(docks)}</div>
            <div><b>Covered Incidents:</b> {len(incidents_covered)} ({len(incidents_covered) / len(incidents) * 100:.2f}%)</div>
            <div><b>Uncovered Incidents:</b> {len(uncovered_incidents)} ({len(uncovered_incidents) / len(incidents) * 100:.2f}%)</div>
            <div style="margin-top: 8px;">
                <span style="color:{INCIDENT_COVERED_COLOR};">&#9679;</span> Covered incident
                <span style="margin-left: 10px; color:{INCIDENT_UNCOVERED_COLOR};">&#9679;</span> Uncovered incident
            </div>
            <div>
                <span style="color:{DOCK_COLOR};">&#9679;</span> Dock
                <span style="margin-left: 10px; color:{PRIORITY_DOCK_BORDER_COLOR};">&#9679;</span> Priority dock
            </div>
        </div>
        """
        map.get_root().html.add_child(folium.Element(legend_html))
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        map.save(str(OUTPUT_DIR / f"{map_name}.html"))
    except Exception as e:
        print(f"Error creating map: {e}")
