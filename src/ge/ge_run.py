from __future__ import annotations

import os
from pathlib import Path
import duckdb

YEAR = os.getenv("TLC_YEAR", "2025")
MONTH = os.getenv("TLC_MONTH", "12")
DATASET = os.getenv("TLC_DATASET", "yellow")

BRONZE_FILE = Path("data") / "bronze" / f"dataset={DATASET}" / f"year={YEAR}" / f"month={MONTH}" / "trips.parquet"

def main() -> None:
    if not BRONZE_FILE.exists():
        raise FileNotFoundError(f"Bronze file not found: {BRONZE_FILE}")

    con = duckdb.connect(database="data/lakehouse.duckdb")

    # Minimal quality checks (fast, production-like gate)
    row_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{BRONZE_FILE.as_posix()}')").fetchone()[0]
    if row_count == 0:
        raise ValueError("GE Gate failed: row_count is 0")

    # Column presence check (dataset-specific - yellow taxi has these commonly)
    cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{BRONZE_FILE.as_posix()}')").fetchall()]
    required = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise ValueError(f"GE Gate failed: missing columns {missing}")

    con.close()
    print(f"[ge_run] PASS: rows={row_count}, required_cols_ok=True")

if __name__ == "__main__":
    main()
