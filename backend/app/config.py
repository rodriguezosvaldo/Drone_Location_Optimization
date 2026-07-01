from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
UPLOADS_DIR = BACKEND_ROOT / "uploads"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"

DEFAULT_DOCKS_PATH = OUTPUT_DIR / "docks_JCPS_MetroSafe.xlsx"
DEFAULT_INCIDENTS_PATH = OUTPUT_DIR / "clean_and_geocoded_LMPD_data_2025.xlsx"

UPLOADED_DOCKS_PATH = UPLOADS_DIR / "docks.xlsx"
UPLOADED_INCIDENTS_PATH = UPLOADS_DIR / "incidents.xlsx"
UPLOADED_PRIORITY_DOCKS_PATH = UPLOADS_DIR / "priority_docks.xlsx"
