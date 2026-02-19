from __future__ import annotations

import json
from datetime import datetime
import requests
import boto3

from src.utils.config import load_config
from src.utils.s3_paths import bronze_key
from src.utils.logging import get_logger

log = get_logger("ingestion")

def bls_fetch(endpoint: str, series_ids: list[str], start_year: int, end_year: int) -> dict:
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
        # optional: registrationkey if you have one (not required for small usage)
        # "registrationkey": "YOUR_KEY"
    }
    r = requests.post(endpoint, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def main() -> None:
    cfg = load_config()
    aws = cfg["aws"]
    bls = cfg["bls"]

    session = boto3.Session(region_name=aws["region"])
    s3 = session.client("s3")

    data = bls_fetch(bls["endpoint"], bls["series"], bls["start_year"], bls["end_year"])

    if "Results" not in data or "series" not in data["Results"]:
        raise RuntimeError(f"Unexpected BLS response: {list(data.keys())}")

    bucket = aws["s3_bucket"]
    prefix = aws["bronze_prefix"]

    now = datetime.utcnow().isoformat()

    # Write each (series_id, year, month) as one JSON object into partitioned S3 key
    for series in data["Results"]["series"]:
        sid = series["seriesID"]
        for item in series.get("data", []):
            year = int(item["year"])
            period = item["period"]  # e.g., "M01"
            if not period.startswith("M"):
                continue
            month = int(period[1:])

            record = {
                "ingested_at_utc": now,
                "series_id": sid,
                "year": year,
                "month": month,
                "value": item.get("value"),
                "footnotes": item.get("footnotes", []),
            }

            key = bronze_key(prefix, sid, year, month)
            body = json.dumps(record).encode("utf-8")

            log.info("Uploading bronze: s3://%s/%s", bucket, key)
            s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")

    log.info("DONE bronze ingestion.")

if __name__ == "__main__":
    main()
