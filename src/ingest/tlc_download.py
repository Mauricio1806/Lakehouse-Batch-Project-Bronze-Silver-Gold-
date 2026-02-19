from __future__ import annotations

import os
from pathlib import Path
import urllib.request

# Download a recent month (keep it small enough for local)
# Adjust if needed: e.g., 2025-12, 2026-01, etc.
YEAR = os.getenv("TLC_YEAR", "2025")
MONTH = os.getenv("TLC_MONTH", "12")  # 2 digits
DATASET = os.getenv("TLC_DATASET", "yellow")  # yellow or green (default yellow)

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
FILENAME = f"{DATASET}_tripdata_{YEAR}-{MONTH}.parquet"
URL = f"{BASE_URL}/{FILENAME}"

RAW_DIR = Path("data") / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = RAW_DIR / FILENAME

def main() -> None:
    if OUT_PATH.exists() and OUT_PATH.stat().st_size > 0:
        print(f"[tlc_download] OK already exists: {OUT_PATH}")
        return

    print(f"[tlc_download] Downloading: {URL}")
    urllib.request.urlretrieve(URL, OUT_PATH)
    print(f"[tlc_download] Saved to: {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
