from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppSession:
    docks: list[Any] | None = None
    incidents: list[Any] | None = None
    incidents_by_month: dict | None = None
    docks_path: Path | None = None
    incidents_path: Path | None = None
    docks_count: int = 0
    incidents_count: int = 0
    loaded: bool = False


session = AppSession()
