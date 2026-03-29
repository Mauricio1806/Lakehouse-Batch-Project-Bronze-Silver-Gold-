from __future__ import annotations
from pathlib import Path

# Resolve project root as two levels above this file (src/utils/paths.py → root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR    = PROJECT_ROOT / "data"
RAW_DIR     = DATA_DIR / "raw"
BRONZE_DIR  = DATA_DIR / "bronze"
SILVER_DIR  = DATA_DIR / "silver"
GOLD_DIR    = DATA_DIR / "gold"
LAKEHOUSE_DB = DATA_DIR / "lakehouse.duckdb"

DBT_PROJECT  = PROJECT_ROOT / "dbt" / "lakehouse_dbt"
