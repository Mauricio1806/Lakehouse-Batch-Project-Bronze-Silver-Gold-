"""
grafana_export.py
-----------------
Export Gold Parquet tables to JSON files for Grafana Infinity datasource.

Usage (inside Docker or locally):
    python src/analytics/grafana_export.py

Environment variables:
    LAKEHOUSE_ROOT    — root directory (default: /opt/airflow)
    LAKEHOUSE_DB_PATH — DuckDB database path (default: /opt/airflow/lakehouse.duckdb)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LAKEHOUSE_ROOT = os.environ.get("LAKEHOUSE_ROOT", "/opt/airflow")
LAKEHOUSE_DB_PATH = os.environ.get("LAKEHOUSE_DB_PATH", "/opt/airflow/lakehouse.duckdb")

GOLD_DIR = Path("/opt/airflow/data/gold")
OUTPUT_DIR = Path(LAKEHOUSE_ROOT) / "grafana" / "data"

GOLD_TABLES = {
    "revenue_daily": "mart_revenue_daily.parquet",
    "trips_by_hour": "mart_trips_by_hour.parquet",
    "trips_by_location": "mart_trips_by_location.parquet",
    "payment_breakdown": "mart_payment_breakdown.parquet",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FloatEncoder(json.JSONEncoder):
    """Serialize floats with 2 decimal places; fall back to str for unknown types."""

    def default(self, obj):  # noqa: D102
        return str(obj)

    def iterencode(self, obj, _one_shot=False):  # type: ignore[override]
        # Round float values to 2 decimal places during encoding
        return super().iterencode(_round_floats(obj), _one_shot)


def _round_floats(obj):
    """Recursively round all float values in a nested structure."""
    if isinstance(obj, float):
        return round(obj, 2)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(i) for i in obj]
    return obj


def _serialize(obj):
    """JSON default serializer — converts dates/datetimes to ISO strings."""
    return str(obj)


def _to_records(relation) -> list[dict]:
    """Convert a DuckDB relation to a list of plain Python dicts."""
    df = relation.df()
    return json.loads(
        df.to_json(orient="records", date_format="iso", default_handler=str)
    )


# ---------------------------------------------------------------------------
# Main export
# ---------------------------------------------------------------------------

def export_tables(con: duckdb.DuckDBPyConnection) -> dict[str, list[dict]]:
    """Read all Gold Parquet files and return {table_name: [records]}."""
    tables: dict[str, list[dict]] = {}

    for table_key, filename in GOLD_TABLES.items():
        parquet_path = GOLD_DIR / filename
        print(f"  Reading: {parquet_path}")

        rel = con.execute(
            f"SELECT * FROM read_parquet('{parquet_path.as_posix()}')"
        )
        records = _to_records(rel)
        tables[table_key] = records
        print(f"    -> {len(records):,} rows exported to {table_key}.json")

    return tables


def write_json(output_dir: Path, name: str, data) -> None:
    """Write *data* as pretty-printed JSON to *output_dir/name.json*."""
    out_path = output_dir / f"{name}.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(
            _round_floats(data),
            fh,
            indent=2,
            default=_serialize,
        )
    print(f"  Written: {out_path}")


def compute_summary(revenue_records: list[dict]) -> dict:
    """Compute KPI summary from daily revenue records."""
    if not revenue_records:
        return {
            "total_revenue": 0.0,
            "total_trips": 0,
            "avg_fare": 0.0,
            "peak_day": None,
            "peak_day_trips": 0,
            "data_quality_pct": 98.7,
        }

    total_revenue = sum(r.get("total_revenue") or 0 for r in revenue_records)
    total_trips = sum(r.get("total_trips") or 0 for r in revenue_records)
    total_fare = sum(r.get("total_fare") or 0 for r in revenue_records)

    # Weighted average fare: sum(total_fare) / sum(total_trips)
    avg_fare = (total_fare / total_trips) if total_trips > 0 else 0.0

    # Peak day by total_trips
    peak_record = max(revenue_records, key=lambda r: r.get("total_trips") or 0)
    peak_day = peak_record.get("trip_date")
    peak_day_trips = peak_record.get("total_trips") or 0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_trips": int(total_trips),
        "avg_fare": round(avg_fare, 2),
        "peak_day": str(peak_day) if peak_day is not None else None,
        "peak_day_trips": int(peak_day_trips),
        "data_quality_pct": 98.7,  # placeholder — replace with real DQ metric
    }


def main() -> None:
    print("=" * 60)
    print("Grafana Export — Gold Layer → JSON")
    print("=" * 60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory : {OUTPUT_DIR}")
    print(f"DuckDB path      : {LAKEHOUSE_DB_PATH}")
    print(f"Gold Parquet dir : {GOLD_DIR}")
    print()

    # Connect to DuckDB (read-only if DB file exists; in-memory otherwise)
    db_path = Path(LAKEHOUSE_DB_PATH)
    if db_path.exists():
        con = duckdb.connect(str(db_path), read_only=True)
    else:
        print(f"  WARNING: DuckDB file not found at {db_path}; using in-memory instance.")
        con = duckdb.connect()

    try:
        print("Exporting Gold tables...")
        tables = export_tables(con)

        print("\nWriting JSON files...")
        for table_key, records in tables.items():
            write_json(OUTPUT_DIR, table_key, records)

        # Compute and write KPI summary
        print("\nComputing summary KPIs...")
        summary = compute_summary(tables.get("revenue_daily", []))
        write_json(OUTPUT_DIR, "summary", summary)
        print("\nSummary KPIs:")
        for k, v in summary.items():
            print(f"  {k}: {v}")

    finally:
        con.close()

    print("\nExport complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
