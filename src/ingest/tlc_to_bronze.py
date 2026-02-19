from __future__ import annotations

import os
from pathlib import Path
import duckdb

YEAR = os.getenv("TLC_YEAR", "2025")
MONTH = os.getenv("TLC_MONTH", "12")
DATASET = os.getenv("TLC_DATASET", "yellow")

RAW_FILE = Path("data") / "raw" / f"{DATASET}_tripdata_{YEAR}-{MONTH}.parquet"
BRONZE_DIR = Path("data_bronze") / f"dataset={DATASET}" / f"year={YEAR}" / f"month={MONTH}"
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

def main() -> None:
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}. Run tlc_download first.")

    out_file = BRONZE_DIR / "trips.parquet"

    con = duckdb.connect(database="data/lakehouse.duckdb")
    con.execute("INSTALL parquet; LOAD parquet;")

    # Write raw parquet into bronze (kept as parquet, partitioned by folders)
    con.execute(
        f\"\"\"
        COPY (
            SELECT * FROM read_parquet('{RAW_FILE.as_posix()}')
        )
        TO '{out_file.as_posix()}'
        (FORMAT PARQUET, CODEC 'SNAPPY');
        \"\"\"
    )
    con.close()

    print(f"[tlc_to_bronze] Bronze written: {out_file}")

if __name__ == "__main__":
    main()
