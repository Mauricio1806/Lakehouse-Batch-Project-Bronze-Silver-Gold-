"""
NYC TLC Lakehouse — Data Profiler
==================================
Inspects Bronze / Silver / Gold layers and prints a structured quality
summary. Also writes reports/profile_YYYYMMDD_HHMMSS.txt.

Usage:  python -m src.analytics.profile
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import duckdb

ROOT       = Path(os.getenv("LAKEHOUSE_ROOT", str(Path(__file__).parents[2])))
DATA_DIR   = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH    = os.getenv("LAKEHOUSE_DB_PATH", str(DATA_DIR / "lakehouse.duckdb"))

BRONZE_GLOB = (DATA_DIR / "bronze" / "**" / "*.parquet").as_posix()
SILVER_FILE = (DATA_DIR / "silver" / "stg_trips.parquet").as_posix()
GOLD_FILES  = {
    "mart_revenue_daily":    (DATA_DIR / "gold" / "mart_revenue_daily.parquet").as_posix(),
    "mart_trips_by_hour":    (DATA_DIR / "gold" / "mart_trips_by_hour.parquet").as_posix(),
    "mart_trips_by_location":(DATA_DIR / "gold" / "mart_trips_by_location.parquet").as_posix(),
    "mart_payment_breakdown":(DATA_DIR / "gold" / "mart_payment_breakdown.parquet").as_posix(),
}


def _div(label: str = "", width: int = 60) -> str:
    return f"\n{'─' * width}  {label}\n" if label else f"\n{'─' * 60}\n"


def _safe(con, sql: str, default=None):
    try:
        return con.execute(sql).fetchall()
    except Exception as exc:
        print(f"  [WARN] {exc}")
        return default or []


def profile_layer(con, name: str, path: str) -> list[str]:
    lines = [_div(name)]
    rows = _safe(con, f"SELECT COUNT(*) FROM read_parquet('{path}')")
    n = rows[0][0] if rows else 0
    lines.append(f"  Row count   : {n:,}")

    desc = _safe(con, f"DESCRIBE SELECT * FROM read_parquet('{path}')")
    if desc:
        lines.append(f"  Columns     : {len(desc)}")
        col_names = [r[0] for r in desc]
        lines.append(f"  Column list : {', '.join(col_names)}")

    if n > 0:
        numeric_cols = [r[0] for r in desc if r[1].upper() in
                        ("BIGINT","INTEGER","INT","DOUBLE","FLOAT","DECIMAL","HUGEINT","UBIGINT")]
        for col in numeric_cols[:6]:
            stats = _safe(con, f"""
                SELECT
                    MIN({col}), MAX({col}),
                    ROUND(AVG({col}), 4),
                    SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS nulls
                FROM read_parquet('{path}')
            """)
            if stats and stats[0]:
                mn, mx, av, nl = stats[0]
                null_pct = round(nl / n * 100, 2) if n else 0
                lines.append(
                    f"  [{col:<28}]  min={mn}  max={mx}  avg={av}  nulls={nl} ({null_pct}%)"
                )
    return lines


def main() -> None:
    con = duckdb.connect(DB_PATH)
    ts  = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    out_lines: list[str] = []

    header = [
        "=" * 60,
        "  NYC TLC LAKEHOUSE — DATA PROFILE",
        f"  Generated : {ts}",
        f"  DuckDB DB : {DB_PATH}",
        "=" * 60,
    ]
    out_lines += header

    # Bronze
    out_lines += profile_layer(con, "BRONZE  (raw ingested)", BRONZE_GLOB)

    # Bronze partition info
    part_rows = _safe(con, f"""
        SELECT
            REPLACE(SPLIT_PART(filename, '/', -4), 'dataset=', '') AS dataset,
            REPLACE(SPLIT_PART(filename, '/', -3), 'year=',    '') AS year,
            REPLACE(SPLIT_PART(filename, '/', -2), 'month=',   '') AS month,
            COUNT(*) AS rows
        FROM read_parquet('{BRONZE_GLOB}', filename=true)
        GROUP BY 1,2,3 ORDER BY 2,3
    """)
    if part_rows:
        out_lines.append("  Partitions  :")
        for r in part_rows:
            out_lines.append(f"    dataset={r[0]}  year={r[1]}  month={r[2]}  rows={r[3]:,}")

    # Silver
    out_lines += profile_layer(con, "SILVER  (stg_trips)", SILVER_FILE)

    # Silver date range & dedup stats
    silver_stats = _safe(con, f"""
        SELECT
            MIN(pickup_datetime)::DATE AS min_date,
            MAX(pickup_datetime)::DATE AS max_date,
            COUNT(DISTINCT DATE_TRUNC('day', pickup_datetime)::DATE) AS days_covered
        FROM read_parquet('{SILVER_FILE}')
    """)
    if silver_stats and silver_stats[0]:
        r = silver_stats[0]
        out_lines.append(f"  Date range  : {r[0]} → {r[1]}  ({r[2]} days)")

    # Gold models
    for model_name, path in GOLD_FILES.items():
        out_lines += profile_layer(con, f"GOLD  ({model_name})", path)

    # Pipeline summary
    bronze_n = _safe(con, f"SELECT COUNT(*) FROM read_parquet('{BRONZE_GLOB}')")
    silver_n = _safe(con, f"SELECT COUNT(*) FROM read_parquet('{SILVER_FILE}')")
    bn = bronze_n[0][0] if bronze_n else 0
    sn = silver_n[0][0] if silver_n else 0
    drop_pct = round((1 - sn / bn) * 100, 2) if bn > 0 else 0
    qual_pct = round(sn / bn * 100, 2) if bn > 0 else 0

    out_lines += [
        _div("PIPELINE SUMMARY"),
        f"  Bronze rows        : {bn:,}",
        f"  Silver rows        : {sn:,}",
        f"  Rows removed       : {bn - sn:,}  ({drop_pct}%  — dedup + quality filters)",
        f"  Data quality score : {qual_pct}%",
        "",
        "=" * 60,
        "  Profile complete.",
        "=" * 60,
    ]

    con.close()

    report = "\n".join(out_lines)
    print(report)

    ts_file = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS_DIR / f"profile_{ts_file}.txt"
    out_path.write_text(report, encoding="utf-8")
    print(f"\n[profile] Saved → {out_path}")


if __name__ == "__main__":
    main()
