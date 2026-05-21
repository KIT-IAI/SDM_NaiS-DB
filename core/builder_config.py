from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
OUTPUT_DIR = DATA_DIR / "output"
DOCS_DIR = PROJECT_ROOT / "docs"


def _resolve_path(default_path: Path, env_name: str) -> Path:
    raw_value = os.environ.get(env_name)
    if not raw_value:
        return default_path

    candidate = Path(raw_value)
    if candidate.is_absolute():
        return candidate

    return PROJECT_ROOT / candidate


RAW_XLSX_DIR = RAW_DIR / "xlsx"
RAW_DB_DIR = RAW_DIR / "db"
INTERMEDIATE_DB_DIR = INTERMEDIATE_DIR / "db"
OUTPUT_DB_DIR = OUTPUT_DIR / "db"
MAIN_DB_PATH = _resolve_path(OUTPUT_DB_DIR / "NaiS_latest.db", "NAIS_DB_PATH")

TABULA_XLSX_PATH = _resolve_path(RAW_XLSX_DIR / "Tabula-NaiS.xlsx", "NAIS_TABULA_XLSX")
IWU_XLSX_PATH = _resolve_path(RAW_XLSX_DIR / "IWU-NWG-NaiS.xlsx", "NAIS_IWU_XLSX")
CRREM_XLSX_PATH = _resolve_path(RAW_XLSX_DIR / "CRREM_Global_Pathways-V2.04.xlsx", "NAIS_CRREM_XLSX")

ALTBAUATLAS_SOURCE_DB_PATH = _resolve_path(RAW_DB_DIR / "altbauatlas.db", "NAIS_ALTBAUATLAS_SOURCE_DB")
ALTBAUATLAS_BACKUP_DB_PATH = _resolve_path(RAW_DB_DIR / "altbauatlas_backup.db", "NAIS_ALTBAUATLAS_BACKUP_DB")
EPD_SOURCE_DB_PATH = _resolve_path(RAW_DB_DIR / "epd.db", "NAIS_EPD_SOURCE_DB")
CRREM_OUTPUT_DB_PATH = _resolve_path(INTERMEDIATE_DB_DIR / "crrem_v204.db", "NAIS_CRREM_OUTPUT_DB")


def ensure_project_dirs() -> None:
    for path in (RAW_XLSX_DIR, RAW_DB_DIR, INTERMEDIATE_DB_DIR, OUTPUT_DB_DIR, DOCS_DIR):
        path.mkdir(parents=True, exist_ok=True)
