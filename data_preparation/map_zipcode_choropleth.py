"""
Folium maps for MetroSafe dock analysis:
  1. Zip-code choropleth colored by incidents-per-dock ratio
  2. Zip-code heatmap colored by incident count (no docks)
  3. Dock utilization map colored/sized by flight takeoff counts

Data sources:
  - LOJIC Jefferson County KY ZIP Codes (GeoJSON)
  - output/Medium_and_High_clean_and_geocoded_LMPD_data_2025_cleaned.xlsx
  - output/docks_JCPS_MetroSafe.xlsx
  - output/clean_and_geocoded_JCPS_schools.xlsx
  - data/Dataflights1.xlsx (dock locations / zip lookup)
  - data/Dataflights.xlsx (flight takeoffs for dock utilization)
"""
from __future__ import annotations

import json
import math
import re
import urllib.request
from pathlib import Path

import folium
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_LMPD_PATH = PROJECT_ROOT / "output" / "Medium_and_High_clean_and_geocoded_LMPD_data_2025_cleaned.xlsx"
DEFAULT_DOCKS_PATH = PROJECT_ROOT / "output" / "docks_JCPS_MetroSafe.xlsx"
DEFAULT_JCPS_PATH = PROJECT_ROOT / "output" / "clean_and_geocoded_JCPS_schools.xlsx"
DEFAULT_DATAFLIGHTS_PATH = PROJECT_ROOT / "data" / "Dataflights1.xlsx"
DEFAULT_FLIGHTS_LOG_PATH = PROJECT_ROOT / "data" / "Dataflights.xlsx"
DEFAULT_GEOJSON_PATH = PROJECT_ROOT / "data" / "geo" / "jefferson_county_zip_codes.geojson"
DEFAULT_OUTPUT_HTML = PROJECT_ROOT / "output" / "incidents_vs_docks_zipcode_map.html"
DEFAULT_INCIDENTS_HEATMAP_HTML = PROJECT_ROOT / "output" / "incidents_by_zipcode_heatmap.html"
DEFAULT_DOCK_UTILIZATION_HTML = PROJECT_ROOT / "output" / "dock_utilization_map.html"

LOJIC_ZIP_GEOJSON_URL = (
    "https://gis.lojic.org/maps/rest/services/LojicSolutions/OpenDataAddresses/"
    "MapServer/3/query?where=1%3D1&outFields=ZIPCODE&f=geojson&outSR=4326"
)

LOUISVILLE_CENTER = [38.2527, -85.7585]
COLOR_LOW = (116, 196, 205)   # light blue (low)
COLOR_HIGH = (215, 48, 39)     # intense red (high)
COLOR_INCIDENTS_NO_DOCKS = "#41ab5d"  # green
COLOR_DOCKS_NO_INCIDENTS = "#ffd92f"  # yellow
NO_DATA_COLOR = "#d9d9d9"
MILES_TO_METERS = 1609.34
DOCK_CIRCLE_DIAMETER_MILES = 1.18
_ZIP_RE = re.compile(r"\b(\d{5})\b")


def extract_zip_from_address(address: object) -> str | None:
    if pd.isna(address):
        return None
    text = str(address)
    match = _ZIP_RE.search(text)
    if match:
        return match.group(1)
    return None


def load_lmpd_data(data_path: Path | str = DEFAULT_LMPD_PATH) -> pd.DataFrame:
    df = pd.read_excel(data_path)
    if "zip_code" in df.columns:
        df["zip_code"] = df["zip_code"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    if "priority" in df.columns:
        df = df.loc[df["priority"].notna()].copy()
    return df.loc[df["zip_code"].notna() & (df["zip_code"] != "nan")].copy()


def load_docks_data(
    docks_path: Path | str = DEFAULT_DOCKS_PATH,
    jcps_path: Path | str = DEFAULT_JCPS_PATH,
    dataflights_path: Path | str = DEFAULT_DATAFLIGHTS_PATH,
) -> pd.DataFrame:
    docks = pd.read_excel(docks_path)
    jcps = pd.read_excel(jcps_path)
    jcps_lookup = (
        jcps[["latitude", "longitude", "zip_code"]]
        .dropna(subset=["latitude", "longitude", "zip_code"])
        .drop_duplicates(subset=["latitude", "longitude"])
    )
    docks = docks.merge(jcps_lookup, on=["latitude", "longitude"], how="left")

    flights_path = Path(dataflights_path)
    if flights_path.exists():
        flights = pd.read_excel(flights_path)
        flights_lookup = flights.rename(
            columns={"Takeoff Latitude": "latitude", "Takeoff Longitude": "longitude"}
        )
        flights_lookup["zip_code_flight"] = flights_lookup["Takeoff Address"].map(extract_zip_from_address)
        docks = docks.merge(
            flights_lookup[["latitude", "longitude", "zip_code_flight"]],
            on=["latitude", "longitude"],
            how="left",
        )
        docks["zip_code"] = docks["zip_code"].fillna(docks["zip_code_flight"])
        docks = docks.drop(columns=["zip_code_flight"], errors="ignore")

    docks["zip_code"] = docks["zip_code"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    return docks.loc[docks["zip_code"].notna() & (docks["zip_code"] != "nan")].copy()


def ensure_zip_geojson(geojson_path: Path | str = DEFAULT_GEOJSON_PATH) -> Path:
    """Download and cache Jefferson County zip polygons from LOJIC if needed."""
    path = Path(geojson_path)
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(LOJIC_ZIP_GEOJSON_URL, timeout=120) as response:
        geojson = json.load(response)

    path.write_text(json.dumps(geojson), encoding="utf-8")
    return path


def _counts_by_zip(df: pd.DataFrame) -> pd.Series:
    return df["zip_code"].astype(str).value_counts()


def build_zip_ratio_stats(df_lmpd: pd.DataFrame, df_docks: pd.DataFrame) -> pd.DataFrame:
    """Incidents, docks, and incidents-per-dock ratio for each zip code."""
    incidents = _counts_by_zip(df_lmpd)
    docks = _counts_by_zip(df_docks)
    zip_codes = sorted(set(incidents.index) | set(docks.index))

    rows = []
    for zip_code in zip_codes:
        inc = int(incidents.get(zip_code, 0))
        dock_count = int(docks.get(zip_code, 0))
        ratio = (inc / dock_count) if inc > 0 and dock_count > 0 else None
        rows.append(
            {
                "zip_code": zip_code,
                "incidents": inc,
                "docks": dock_count,
                "ratio": ratio,
            }
        )
    return pd.DataFrame(rows)


def build_zip_incident_stats(df_lmpd: pd.DataFrame) -> pd.DataFrame:
    """Incident counts for each zip code."""
    incidents = _counts_by_zip(df_lmpd)
    return pd.DataFrame(
        {
            "zip_code": incidents.index.astype(str),
            "incidents": incidents.values.astype(int),
        }
    ).sort_values("zip_code").reset_index(drop=True)


def _zip_fill_color(incidents: int, docks: int, ratio: float | None, vmin: float, vmax: float) -> str:
    if incidents > 0 and docks == 0:
        return COLOR_INCIDENTS_NO_DOCKS
    if docks > 0 and incidents == 0:
        return COLOR_DOCKS_NO_INCIDENTS
    if incidents > 0 and docks > 0 and ratio is not None:
        return _ratio_to_color(float(ratio), vmin, vmax)
    return NO_DATA_COLOR


def _ratio_to_color(ratio: float, vmin: float, vmax: float) -> str:
    if vmax <= vmin:
        t = 0.5
    else:
        t = (ratio - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    r = int(COLOR_LOW[0] + t * (COLOR_HIGH[0] - COLOR_LOW[0]))
    g = int(COLOR_LOW[1] + t * (COLOR_HIGH[1] - COLOR_LOW[1]))
    b = int(COLOR_LOW[2] + t * (COLOR_HIGH[2] - COLOR_LOW[2]))
    return f"#{r:02x}{g:02x}{b:02x}"


def load_dock_utilization(
    flights_path: Path | str = DEFAULT_FLIGHTS_LOG_PATH,
    *,
    merge_distance_miles: float = 0.05,
) -> pd.DataFrame:
    """Aggregate flight takeoffs by dock address (median lat/lon for GPS jitter).

    Docks within ``merge_distance_miles`` are merged so co-located GPS points
    (e.g. mis-tagged addresses) do not stack overlapping labels.
    """
    df = pd.read_excel(flights_path)
    required = {"Takeoff Address", "Takeoff Latitude", "Takeoff Longitude"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Flight log missing columns: {sorted(missing)}")

    usable = df.dropna(subset=["Takeoff Address", "Takeoff Latitude", "Takeoff Longitude"]).copy()
    usable["Takeoff Address"] = usable["Takeoff Address"].astype(str).str.strip()
    usable = usable.loc[usable["Takeoff Address"] != ""].copy()

    stats = (
        usable.groupby("Takeoff Address", as_index=False)
        .agg(
            latitude=("Takeoff Latitude", "median"),
            longitude=("Takeoff Longitude", "median"),
            flights=("Takeoff Address", "size"),
        )
        .sort_values("flights", ascending=False)
        .reset_index(drop=True)
    )
    stats["zip_code"] = stats["Takeoff Address"].map(extract_zip_from_address)
    stats["short_name"] = stats["Takeoff Address"].str.split(",").str[0].str.strip()
    return _merge_nearby_docks(stats, merge_distance_miles=merge_distance_miles)


def _miles_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    delta_lat = abs(lat1 - lat2) * 69.0
    mean_lat = (lat1 + lat2) / 2.0
    delta_lon = abs(lon1 - lon2) * abs(math.cos(math.radians(mean_lat))) * 69.0
    return (delta_lat**2 + delta_lon**2) ** 0.5


def _merge_nearby_docks(
    stats: pd.DataFrame,
    *,
    merge_distance_miles: float = 0.05,
) -> pd.DataFrame:
    """Merge docks within a short distance; keep the busiest address as the label."""
    if stats.empty or merge_distance_miles <= 0:
        return stats

    ordered = stats.sort_values("flights", ascending=False).reset_index(drop=True)
    used: set[int] = set()
    merged_rows: list[dict] = []

    for i, primary in ordered.iterrows():
        if i in used:
            continue
        cluster = [i]
        for j in range(i + 1, len(ordered)):
            if j in used:
                continue
            other = ordered.loc[j]
            if (
                _miles_between(
                    float(primary["latitude"]),
                    float(primary["longitude"]),
                    float(other["latitude"]),
                    float(other["longitude"]),
                )
                <= merge_distance_miles
            ):
                cluster.append(j)

        used.update(cluster)
        members = ordered.loc[cluster]
        total_flights = int(members["flights"].sum())
        extra_names = [
            name
            for name in members["short_name"].tolist()
            if name != primary["short_name"]
        ]
        label = primary["short_name"]
        if extra_names:
            label = f"{primary['short_name']} (+{len(extra_names)} nearby)"

        merged_rows.append(
            {
                "Takeoff Address": primary["Takeoff Address"],
                "latitude": float(primary["latitude"]),
                "longitude": float(primary["longitude"]),
                "flights": total_flights,
                "zip_code": primary["zip_code"],
                "short_name": label,
            }
        )

    return (
        pd.DataFrame(merged_rows)
        .sort_values("flights", ascending=False)
        .reset_index(drop=True)
    )


def _dock_utilization_legend_html(vmin: float, vmax: float, diameter_miles: float) -> str:
    return f"""
    <div style="
        position: fixed;
        bottom: 25px;
        left: 25px;
        z-index: 1000;
        background-color: white;
        border: 2px solid #666;
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 13px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        max-width: 280px;
    ">
        <div style="font-weight: bold; margin-bottom: 8px;">
            Dock utilization (takeoffs)
        </div>
        <div style="
            height: 16px;
            width: 220px;
            background: linear-gradient(to right, rgb({COLOR_LOW[0]},{COLOR_LOW[1]},{COLOR_LOW[2]}), rgb({COLOR_HIGH[0]},{COLOR_HIGH[1]},{COLOR_HIGH[2]}));
            border: 1px solid #666;
            margin-bottom: 6px;
        "></div>
        <div style="display: flex; justify-content: space-between; width: 220px;">
            <span>Fewer<br>{int(vmin)}</span>
            <span>More<br>{int(vmax)}</span>
        </div>
        <div style="margin-top: 8px; color: #555;">
            Color scales with flight count.<br>
            Circles are fixed at {diameter_miles:.2f} mi diameter.<br>
            Red = most used docks
        </div>
    </div>
    """


def create_dock_utilization_map(
    dock_stats: pd.DataFrame | None = None,
    *,
    flights_path: Path | str = DEFAULT_FLIGHTS_LOG_PATH,
    geojson_path: Path | str = DEFAULT_GEOJSON_PATH,
    output_path: Path | str = DEFAULT_DOCK_UTILIZATION_HTML,
    show_zip_boundaries: bool = True,
    circle_diameter_miles: float = DOCK_CIRCLE_DIAMETER_MILES,
) -> folium.Map:
    """Build a Folium map of docks colored by takeoff count; all circles share a fixed geographic diameter."""
    dock_stats = dock_stats if dock_stats is not None else load_dock_utilization(flights_path)
    if dock_stats.empty:
        raise ValueError("No dock utilization rows to map.")

    vmin = float(dock_stats["flights"].min())
    vmax = float(dock_stats["flights"].max())
    radius_meters = (circle_diameter_miles / 2.0) * MILES_TO_METERS

    folium_map = folium.Map(location=LOUISVILLE_CENTER, zoom_start=11, tiles="CartoDB Positron")

    if show_zip_boundaries:
        geojson_file = ensure_zip_geojson(geojson_path)
        with geojson_file.open(encoding="utf-8") as handle:
            geojson = json.load(handle)
        folium.GeoJson(
            geojson,
            style_function=lambda _feature: {
                "fillColor": "#f0f0f0",
                "color": "#9e9e9e",
                "weight": 1,
                "fillOpacity": 0.15,
            },
        ).add_to(folium_map)

    for _, row in dock_stats.iterrows():
        flights = int(row["flights"])
        color = _ratio_to_color(float(flights), vmin, vmax)
        zip_label = row["zip_code"] if pd.notna(row["zip_code"]) else "N/A"
        popup_html = f"""
        <div style="font-size: 13px; min-width: 180px;">
            <b>{row["short_name"]}</b><br>
            Flights: <b>{flights}</b><br>
            Zip: {zip_label}<br>
            Circle diameter: {circle_diameter_miles:.2f} mi
        </div>
        """
        folium.Circle(
            location=[float(row["latitude"]), float(row["longitude"])],
            radius=radius_meters,
            color="#333333",
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.55,
            tooltip=f"{row['short_name']}: {flights} flights",
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(folium_map)

    folium_map.get_root().html.add_child(
        folium.Element(_dock_utilization_legend_html(vmin, vmax, circle_diameter_miles))
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    folium_map.save(str(output))
    print(f"Saved dock utilization map to {output}")
    return folium_map


def _geometry_centroid(geometry: dict) -> tuple[float, float] | None:
    if geometry["type"] == "Polygon":
        rings = [geometry["coordinates"][0]]
    elif geometry["type"] == "MultiPolygon":
        rings = [polygon[0] for polygon in geometry["coordinates"]]
    else:
        return None

    largest_ring = max(rings, key=len)
    lons = [point[0] for point in largest_ring]
    lats = [point[1] for point in largest_ring]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def _attach_stats_to_geojson(geojson: dict, stats: pd.DataFrame) -> dict:
    stats_by_zip = stats.set_index("zip_code")
    enriched = json.loads(json.dumps(geojson))

    for feature in enriched["features"]:
        zip_code = str(feature["properties"].get("ZIPCODE", "")).strip()
        if zip_code in stats_by_zip.index:
            row = stats_by_zip.loc[zip_code]
            feature["properties"]["incidents"] = int(row["incidents"])
            feature["properties"]["docks"] = int(row["docks"])
            feature["properties"]["ratio"] = (
                round(float(row["ratio"]), 2) if pd.notna(row["ratio"]) else None
            )
        else:
            feature["properties"]["incidents"] = 0
            feature["properties"]["docks"] = 0
            feature["properties"]["ratio"] = None

    return enriched


def _attach_incident_counts_to_geojson(geojson: dict, stats: pd.DataFrame) -> dict:
    stats_by_zip = stats.set_index("zip_code")
    enriched = json.loads(json.dumps(geojson))

    for feature in enriched["features"]:
        zip_code = str(feature["properties"].get("ZIPCODE", "")).strip()
        if zip_code in stats_by_zip.index:
            feature["properties"]["incidents"] = int(stats_by_zip.loc[zip_code, "incidents"])
        else:
            feature["properties"]["incidents"] = 0

    return enriched


def _legend_html(vmin: float, vmax: float) -> str:
    return f"""
    <div style="
        position: fixed;
        bottom: 25px;
        left: 25px;
        z-index: 1000;
        background-color: white;
        border: 2px solid #666;
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 13px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        max-width: 280px;
    ">
        <div style="font-weight: bold; margin-bottom: 8px;">
            Incidents per dock location
        </div>
        <div style="
            height: 16px;
            width: 220px;
            background: linear-gradient(to right, rgb({COLOR_LOW[0]},{COLOR_LOW[1]},{COLOR_LOW[2]}), rgb({COLOR_HIGH[0]},{COLOR_HIGH[1]},{COLOR_HIGH[2]}));
            border: 1px solid #666;
            margin-bottom: 6px;
        "></div>
        <div style="display: flex; justify-content: space-between; width: 220px;">
            <span>Lower<br>{vmin:.1f}</span>
            <span>Higher<br>{vmax:.1f}</span>
        </div>
        <div style="margin-top: 8px; color: #555;">
            Gradient (both present): red = more incidents per dock<br>
            Blue = fewer incidents per dock
        </div>
        <div style="margin-top: 8px;">
            <span style="display:inline-block;width:14px;height:14px;background:{COLOR_INCIDENTS_NO_DOCKS};border:1px solid #666;margin-right:6px;"></span>
            Incidents, no docks
        </div>
        <div style="margin-top: 4px;">
            <span style="display:inline-block;width:14px;height:14px;background:{COLOR_DOCKS_NO_INCIDENTS};border:1px solid #666;margin-right:6px;"></span>
            Docks, no incidents
        </div>
        <div style="margin-top: 6px; color: #777;">
            Gray = no incident/dock data in dataset
        </div>
    </div>
    """


def _incidents_heatmap_legend_html(vmin: float, vmax: float) -> str:
    return f"""
    <div style="
        position: fixed;
        bottom: 25px;
        left: 25px;
        z-index: 1000;
        background-color: white;
        border: 2px solid #666;
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 13px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        max-width: 280px;
    ">
        <div style="font-weight: bold; margin-bottom: 8px;">
            Incidents by zip code
        </div>
        <div style="
            height: 16px;
            width: 220px;
            background: linear-gradient(to right, rgb({COLOR_LOW[0]},{COLOR_LOW[1]},{COLOR_LOW[2]}), rgb({COLOR_HIGH[0]},{COLOR_HIGH[1]},{COLOR_HIGH[2]}));
            border: 1px solid #666;
            margin-bottom: 6px;
        "></div>
        <div style="display: flex; justify-content: space-between; width: 220px;">
            <span>Fewer<br>{int(vmin)}</span>
            <span>More<br>{int(vmax)}</span>
        </div>
        <div style="margin-top: 8px; color: #555;">
            Blue = fewer incidents<br>
            Red = more incidents
        </div>
        <div style="margin-top: 6px; color: #777;">
            Gray = no incidents in dataset
        </div>
    </div>
    """


def _add_zip_labels(folium_map: folium.Map, geojson: dict) -> None:
    labeled_zips: set[str] = set()
    for feature in geojson["features"]:
        zip_code = str(feature["properties"].get("ZIPCODE", "")).strip()
        if not zip_code or zip_code in labeled_zips:
            continue
        centroid = _geometry_centroid(feature["geometry"])
        if centroid is None:
            continue
        labeled_zips.add(zip_code)
        folium.Marker(
            location=centroid,
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    font-size: 11px;
                    font-weight: 700;
                    color: #1f4e79;
                    text-align: center;
                    text-shadow: 1px 1px 2px white, -1px -1px 2px white;
                    width: 48px;
                ">{zip_code}</div>
                """,
                icon_size=(48, 14),
                icon_anchor=(24, 7),
            ),
        ).add_to(folium_map)


def create_zipcode_choropleth_map(
    df_lmpd: pd.DataFrame | None = None,
    df_docks: pd.DataFrame | None = None,
    *,
    geojson_path: Path | str = DEFAULT_GEOJSON_PATH,
    output_path: Path | str = DEFAULT_OUTPUT_HTML,
    show_zip_labels: bool = False,
) -> folium.Map:
    """Build a Folium map with zip polygons colored by incidents-per-dock ratio."""
    df_lmpd = df_lmpd if df_lmpd is not None else load_lmpd_data()
    df_docks = df_docks if df_docks is not None else load_docks_data()
    stats = build_zip_ratio_stats(df_lmpd, df_docks)

    geojson_file = ensure_zip_geojson(geojson_path)
    with geojson_file.open(encoding="utf-8") as handle:
        geojson = json.load(handle)

    enriched_geojson = _attach_stats_to_geojson(geojson, stats)
    both_present = stats.loc[(stats["incidents"] > 0) & (stats["docks"] > 0), "ratio"]
    vmin = float(both_present.min()) if not both_present.empty else 0.0
    vmax = float(both_present.max()) if not both_present.empty else 1.0

    def style_function(feature: dict) -> dict:
        incidents = int(feature["properties"].get("incidents", 0))
        docks = int(feature["properties"].get("docks", 0))
        ratio = feature["properties"].get("ratio")
        fill_color = _zip_fill_color(incidents, docks, ratio, vmin, vmax)
        return {
            "fillColor": fill_color,
            "color": "#4d4d4d",
            "weight": 1.2,
            "fillOpacity": 0.78,
        }

    folium_map = folium.Map(location=LOUISVILLE_CENTER, zoom_start=10, tiles="CartoDB Positron")

    folium.GeoJson(
        enriched_geojson,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["ZIPCODE", "incidents", "docks", "ratio"],
            aliases=["Zip code", "Incidents", "Dock locations", "Incidents per dock"],
            localize=True,
            sticky=False,
        ),
    ).add_to(folium_map)

    if show_zip_labels:
        _add_zip_labels(folium_map, enriched_geojson)

    folium_map.get_root().html.add_child(folium.Element(_legend_html(vmin, vmax)))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    folium_map.save(str(output))
    print(f"Saved zip code choropleth map to {output}")
    return folium_map


def create_incidents_by_zipcode_heatmap(
    df_lmpd: pd.DataFrame | None = None,
    *,
    geojson_path: Path | str = DEFAULT_GEOJSON_PATH,
    output_path: Path | str = DEFAULT_INCIDENTS_HEATMAP_HTML,
    show_zip_labels: bool = False,
) -> folium.Map:
    """Build a Folium map with zip polygons colored by incident count only."""
    df_lmpd = df_lmpd if df_lmpd is not None else load_lmpd_data()
    stats = build_zip_incident_stats(df_lmpd)

    geojson_file = ensure_zip_geojson(geojson_path)
    with geojson_file.open(encoding="utf-8") as handle:
        geojson = json.load(handle)

    enriched_geojson = _attach_incident_counts_to_geojson(geojson, stats)
    positive = stats.loc[stats["incidents"] > 0, "incidents"]
    vmin = float(positive.min()) if not positive.empty else 0.0
    vmax = float(positive.max()) if not positive.empty else 1.0

    def style_function(feature: dict) -> dict:
        incidents = int(feature["properties"].get("incidents", 0))
        fill_color = (
            _ratio_to_color(float(incidents), vmin, vmax)
            if incidents > 0
            else NO_DATA_COLOR
        )
        return {
            "fillColor": fill_color,
            "color": "#4d4d4d",
            "weight": 1.2,
            "fillOpacity": 0.78,
        }

    folium_map = folium.Map(location=LOUISVILLE_CENTER, zoom_start=10, tiles="CartoDB Positron")

    folium.GeoJson(
        enriched_geojson,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["ZIPCODE", "incidents"],
            aliases=["Zip code", "Incidents"],
            localize=True,
            sticky=False,
        ),
    ).add_to(folium_map)

    if show_zip_labels:
        _add_zip_labels(folium_map, enriched_geojson)

    folium_map.get_root().html.add_child(
        folium.Element(_incidents_heatmap_legend_html(vmin, vmax))
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    folium_map.save(str(output))
    print(f"Saved incidents-by-zipcode heatmap to {output}")
    return folium_map


if __name__ == "__main__":
    create_zipcode_choropleth_map()
    create_incidents_by_zipcode_heatmap()
    create_dock_utilization_map()
