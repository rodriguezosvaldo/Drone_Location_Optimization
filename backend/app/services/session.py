from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppSession:
    docks: list[Any] | None = None
    all_incidents: list[Any] | None = None
    incidents_in_one_day: list[Any] | None = None
    priority_area_docks: list[Any] | None = None
    priority_area_all_incidents: list[Any] | None = None
    priority_area_peak_incidents: list[Any] | None = None
    priority_area_bounds: dict[str, float] | None = None
    active_docks: list[Any] | None = None
    active_incidents: list[Any] | None = None
    area_mode: str | None = None
    area_bounds: dict[str, float] | None = None
    docks_path: Path | None = None
    incidents_path: Path | None = None
    docks_count: int = 0
    all_incidents_count: int = 0
    full_peak_incidents_count: int = 0
    priority_area_all_incidents_count: int = 0
    priority_area_peak_incidents_count: int = 0
    priority_dock_names: list[str] | None = None
    analyzed: bool = False
    loaded: bool = False


session = AppSession()
