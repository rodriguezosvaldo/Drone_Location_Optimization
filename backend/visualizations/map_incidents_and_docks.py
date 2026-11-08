from pathlib import Path
import folium
from branca.element import MacroElement, Template

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

def _dock_popup(dock, covered_incidents):
    return folium.Popup(
        html=f"""
        <div style="padding-x:2px; white-space: nowrap;">
            <b>{dock.name}</b><br>
            Effective Radius: {dock.effective_radius:.2f} miles<br>
            Covered Incidents: {len(covered_incidents)}
        </div>
        """,
        max_width=200,
    )

def _add_dock_center_marker(parent, dock, border_color, fill_color, is_priority, covered_incidents):
    popup = _dock_popup(dock, covered_incidents)
    if is_priority:
        folium.Marker(
            location=[dock.latitude, dock.longitude],
            icon=folium.DivIcon(
                html=f"""
                <div style="text-align: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24">
                        <path d="M12 3L2 12h3v8h14v-8h3L12 3z"
                              fill="{fill_color}" stroke="{border_color}" stroke-width="1.5"/>
                    </svg>
                </div>
                """,
                icon_size=(18, 18),
                icon_anchor=(9, 9),
            ),
            popup=popup,
        ).add_to(parent)
    else:
        folium.Marker(
            location=[dock.latitude, dock.longitude],
            icon=folium.DivIcon(
                html=f"""
                <div style="text-align: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24">
                        <polygon points="12,2 22,12 12,22 2,12"
                                 fill="{border_color}" stroke="{border_color}" stroke-width="1.5"/>
                    </svg>
                </div>
                """,
                icon_size=(14, 14),
                icon_anchor=(7, 7),
            ),
            popup=popup,
        ).add_to(parent)

def _add_incident_marker(parent, incident, color):
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
    ).add_to(parent)


class _BindLayerToggles(MacroElement):
    """Bind checkbox toggles after Folium has created the FeatureGroup JS vars."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function() {
            var map = {{ this._parent.get_name() }};
            function bindToggle(checkboxId, layer) {
                var checkbox = document.getElementById(checkboxId);
                if (!checkbox || !layer) return;
                checkbox.addEventListener("change", function() {
                    if (checkbox.checked) {
                        map.addLayer(layer);
                    } else {
                        map.removeLayer(layer);
                    }
                });
            }
            {% for checkbox_id, group_name in this.bindings %}
            bindToggle({{ checkbox_id|tojson }}, {{ group_name }});
            {% endfor %}
        })();
        {% endmacro %}
        """
    )

    def __init__(self, bindings):
        super().__init__()
        self._name = "BindLayerToggles"
        self.bindings = bindings


def _layer_toggle_row(checkbox_id, label, margin_bottom=True):
    margin = "margin-bottom: 5px;" if margin_bottom else ""
    return f"""
        <label for="{checkbox_id}" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; {margin} cursor: pointer; user-select: none; line-height: 1.1;">
            <span>{label}</span>
            <span class="layer-toggle-switch">
                <input type="checkbox" id="{checkbox_id}" checked>
                <span class="layer-toggle-slider"></span>
            </span>
        </label>
    """


def _layer_toggles_panel(layers):
    """Compact layer toggles anchored bottom-right."""
    rows = "".join(
        _layer_toggle_row(checkbox_id, label, margin_bottom=(index < len(layers) - 1))
        for index, (checkbox_id, label, _) in enumerate(layers)
    )
    return f"""
    <div id="layer-toggles-panel" style="
        position: fixed;
        bottom: 25px;
        right: 12px;
        z-index: 1000;
        background-color: white;
        border: 1px solid #888;
        border-radius: 6px;
        padding: 6px 8px;
        font-size: 11px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.18);
        min-width: 118px;
        font-family: system-ui, sans-serif;
    ">
        <div style="font-weight: 600; margin-bottom: 5px; font-size: 11px;">Layers</div>
        {rows}
    </div>
    <style>
        #layer-toggles-panel .layer-toggle-switch {{
            position: relative;
            display: inline-block;
            width: 28px;
            height: 16px;
            flex-shrink: 0;
        }}
        #layer-toggles-panel .layer-toggle-switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        #layer-toggles-panel .layer-toggle-slider {{
            position: absolute;
            cursor: pointer;
            inset: 0;
            background: #4b5563;
            border-radius: 16px;
            transition: 0.15s ease;
            pointer-events: none;
        }}
        #layer-toggles-panel .layer-toggle-slider::before {{
            position: absolute;
            content: "";
            height: 12px;
            width: 12px;
            left: 2px;
            bottom: 2px;
            background: #fff;
            border-radius: 50%;
            transition: 0.15s ease;
        }}
        #layer-toggles-panel input:checked + .layer-toggle-slider {{
            background: #22c55e;
        }}
        #layer-toggles-panel input:checked + .layer-toggle-slider::before {{
            transform: translateX(12px);
        }}
    </style>
    """


def _legend_panel(legend_body_html):
    return f"""
    <div id="map-legend-panel" style="
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
        font-family: system-ui, sans-serif;
    ">
        {legend_body_html}
    </div>
    """

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

        priority_names = set(priority_dock_names or [])
        incidents_group = folium.FeatureGroup(name="Incidents", show=True)
        docks_group = folium.FeatureGroup(name="Docks", show=True)
        priority_docks_group = folium.FeatureGroup(name="Priority docks", show=True)

        uncovered_incidents = [incident for incident in incidents if incident not in incidents_covered]

        for incident in uncovered_incidents:
            _add_incident_marker(incidents_group, incident, INCIDENT_UNCOVERED_COLOR)

        for incident in incidents_covered:
            _add_incident_marker(incidents_group, incident, INCIDENT_COVERED_COLOR)

        for dock in docks:
            dock_radius = dock.effective_radius*1609.34 # convert miles to meters to be able to use the folium library
            if dock_assignments is not None:
                covered_incidents = dock_assignments.get(dock, [])
            else:
                covered_incidents, _ = dock.incidents_covered(incidents_covered)
            is_priority = dock.name in priority_names
            target_group = priority_docks_group if is_priority else docks_group
            border_color, fill_color = _dock_colors(dock, priority_names)
            folium.Circle(
                location=[dock.latitude, dock.longitude],
                radius=dock_radius,
                color=border_color,
                weight=1,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.10,
            ).add_to(target_group)

            _add_dock_center_marker(
                target_group, dock, border_color, fill_color, is_priority, covered_incidents
            )

        incidents_group.add_to(map)
        docks_group.add_to(map)
        priority_docks_group.add_to(map)

        layers = [
            ("toggle-incidents-layer", "Incidents", incidents_group),
            ("toggle-docks-layer", "Docks", docks_group),
            ("toggle-priority-docks-layer", "Priority", priority_docks_group),
        ]
        legend_body = f"""
            <div><b>Total Incidents:</b> {len(incidents)}</div>
            <div><b>Dock Locations:</b> {len(docks)}</div>
            <div><b>Covered Incidents:</b> {len(incidents_covered)} ({len(incidents_covered) / len(incidents) * 100:.2f}%)</div>
            <div><b>Uncovered Incidents:</b> {len(uncovered_incidents)} ({len(uncovered_incidents) / len(incidents) * 100:.2f}%)</div>
            <div style="margin-top: 8px;">
                <span style="color:{INCIDENT_COVERED_COLOR};">&#9679;</span> Covered incident
                <span style="margin-left: 10px; color:{INCIDENT_UNCOVERED_COLOR};">&#9679;</span> Uncovered incident
            </div>
            <div>
                <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" style="vertical-align: middle;"><polygon points="12,2 22,12 12,22 2,12" fill="{DOCK_COLOR}"/></svg> Dock
                <span style="margin-left: 10px; display: inline-flex; align-items: center; gap: 4px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" style="vertical-align: middle;">
                        <path d="M12 3L2 12h3v8h14v-8h3L12 3z"
                              fill="{PRIORITY_DOCK_FILL_COLOR}" stroke="{PRIORITY_DOCK_BORDER_COLOR}" stroke-width="1.5"/>
                    </svg>
                    Priority dock
                </span>
            </div>
        """
        map.get_root().html.add_child(folium.Element(_legend_panel(legend_body)))
        map.get_root().html.add_child(folium.Element(_layer_toggles_panel(layers)))
        _BindLayerToggles(
            [(checkbox_id, group.get_name()) for checkbox_id, _, group in layers]
        ).add_to(map)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        map.save(str(OUTPUT_DIR / f"{map_name}.html"))
    except Exception as e:
        print(f"Error creating map: {e}")
