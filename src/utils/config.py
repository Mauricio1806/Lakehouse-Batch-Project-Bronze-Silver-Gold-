from __future__ import annotations
import os
from pathlib import Path

# ── TLC dataset settings ───────────────────────────────────────────────────
TLC_YEAR    = os.getenv("TLC_YEAR",    "2025")
TLC_MONTH   = os.getenv("TLC_MONTH",   "12")
TLC_DATASET = os.getenv("TLC_DATASET", "yellow")

TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"

# ── AWS settings (Free-Tier safe, us-east-2) ──────────────────────────────
AWS_REGION     = os.getenv("AWS_REGION",     "us-east-2")
S3_BUCKET      = os.getenv("S3_BUCKET",      "your-lakehouse-bucket")
S3_PREFIX      = os.getenv("S3_PREFIX",      "lakehouse")

# ── DuckDB ────────────────────────────────────────────────────────────────
LAKEHOUSE_DB_PATH = os.getenv(
    "LAKEHOUSE_DB_PATH",
    str(Path(__file__).resolve().parents[2] / "data" / "lakehouse.duckdb"),
)
