from __future__ import annotations

def s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key.lstrip('/')}"

def bronze_key(prefix: str, series_id: str, year: int, month: int) -> str:
    # Partition-friendly keys for Athena: .../series_id=XXX/year=YYYY/month=MM/...
    return f"{prefix}/series_id={series_id}/year={year}/month={month:02d}/data.json"

def silver_key(prefix: str, series_id: str, year: int, month: int) -> str:
    return f"{prefix}/series_id={series_id}/year={year}/month={month:02d}/data.parquet"

def gold_key(prefix: str, mart: str, year: int, month: int) -> str:
    return f"{prefix}/mart={mart}/year={year}/month={month:02d}/data.parquet"
