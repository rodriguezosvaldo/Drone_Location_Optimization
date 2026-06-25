"""
Folium choropleth map of Jefferson County zip codes colored by incidents-per-dock ratio.
Data sources:
  - LOJIC Jefferson County KY ZIP Codes (GeoJSON)
  - output/clean_and_geocoded_LMPD_data_2025.xlsx
  - output/docks_JCPS_MetroSafe.xlsx
  - output/clean_and_geocoded_JCPS_schools.xlsx
  - data/Dataflights1.xlsx
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import folium
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_LMPD_PATH = PROJECT_ROOT / "output" / "clean_and_geocoded_LMPD_data_2025.xlsx"
DEFAULT_DOCKS_PATH = PROJECT_ROOT / "output" / "docks_JCPS_MetroSafe.xlsx"
DEFAULT_JCPS_PATH = PROJECT_ROOT / "output" / "clean_and_geocoded_JCPS_schools.xlsx"
DEFAULT_DATAFLIGHTS_PATH = PROJECT_ROOT / "data" / "Dataflights1.xlsx"
DEFAULT_GEOJSON_PATH = PROJECT_ROOT / "data" / "geo" / "jefferson_county_zip_codes.geojson"
DEFAULT_OUTPUT_HTML = PROJECT_ROOT / "output" / "incidents_vs_docks_zipcode_map.html"

LOJIC_ZIP_GEOJSON_URL = (
    "https://gis.lojic.org/maps/rest/services/LojicSolutions/OpenDataAddresses/"
    "MapServer/3/query?where=1%3D1&outFields=ZIPCODE&f=geojson&outSR=4326"
)

LOUISVILLE_CENTER = [38.2527, -85.7585]
COLOR_LOW = (116, 196, 205)   # light blue (low incidents per dock)
COLOR_HIGH = (215, 48, 39)     # intense red (high incidents per dock)
COLOR_INCIDENTS_NO_DOCKS = "#41ab5d"  # green
COLOR_DOCKS_NO_INCIDENTS = "#ffd92f"  # yellow
NO_DATA_COLOR = "#d9d9d9"
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


def create_zipcode_choropleth_map(
    df_lmpd: pd.DataFrame | None = None,
    df_docks: pd.DataFrame | None = None,
    *,
    geojson_path: Path | str = DEFAULT_GEOJSON_PATH,
    output_path: Path | str = DEFAULT_OUTPUT_HTML,
    show_zip_labels: bool = True,
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
        labeled_zips: set[str] = set()
        for feature in enriched_geojson["features"]:
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

    folium_map.get_root().html.add_child(folium.Element(_legend_html(vmin, vmax)))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    folium_map.save(str(output))
    print(f"Saved zip code choropleth map to {output}")
    return folium_map


if __name__ == "__main__":
    create_zipcode_choropleth_map()
