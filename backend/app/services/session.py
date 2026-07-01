from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppSession:
    docks: list[Any] | None = None
    all_incidents: list[Any] | None = None
    incidents_in_one_day: list[Any] | None = None
    active_docks: list[Any] | None = None
    active_incidents: list[Any] | None = None
    area_mode: str | None = None
    area_bounds: dict[str, float] | None = None
    docks_path: Path | None = None
    incidents_path: Path | None = None
    docks_count: int = 0
    incidents_count: int = 0
    analyzed: bool = False
    loaded: bool = False


session = AppSession()
