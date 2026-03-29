# lakehouse-b2s2g

Production-grade **Bronze → Silver → Gold** Lakehouse Batch Pipeline
using the **NYC TLC Trip Record** dataset.

## Stack

| Layer | Tool |
|---|---|
| Storage | Parquet (Snappy) |
| Compute | DuckDB |
| Transformation | dbt-duckdb |
| Quality Gate | Great Expectations (DuckDB-backed) |
| Orchestration | Apache Airflow 2.9 |
| Containerization | Docker Compose |
| Cloud (optional) | AWS S3 + Athena + IAM (us-east-2, Free Tier) |

## Architecture

```
NYC TLC API
    │
    ▼
[01] tlc_download.py     ─── data/raw/yellow_tripdata_YYYY-MM.parquet
    │
    ▼
[02] tlc_to_bronze.py    ─── data/bronze/dataset=yellow/year=*/month=*/trips.parquet
    │
    ▼
[03] ge_run.py           ─── Quality gate (row count, required columns)
    │
    ▼
[04] dbt: stg_trips      ─── data/silver/stg_trips.parquet (clean, cast, dedupe)
    │
    ▼
[05] dbt: mart_revenue   ─── data/gold/mart_revenue_daily.parquet (daily aggregates)
    │
    ▼
    data/lakehouse.duckdb ── Analytical DuckDB querying all layers
```

## Quickstart

### Option A: Docker (recommended)

```bash
# 1. Start Airflow
make up

# 2. Open http://localhost:8080  (admin / admin)
# 3. Trigger the DAG: lakehouse_bronze_silver_gold
```

### Option B: Local Python

```bash
pip install -r requirements.txt
make pipeline
```

## Repo Structure

```
lakehouse-b2s2g/
├── README.md
├── RUNBOOK.md
├── Makefile
├── docker-compose.yml
├── requirements.txt
├── .env
├── data/
│   ├── raw/          ← downloaded TLC parquet files
│   ├── bronze/       ← partitioned by dataset/year/month
│   ├── silver/       ← stg_trips.parquet
│   ├── gold/         ← mart_revenue_daily.parquet
│   └── lakehouse.duckdb
├── src/
│   ├── ingest/
│   │   ├── tlc_download.py
│   │   └── tlc_to_bronze.py
│   ├── ge/
│   │   └── ge_run.py
│   └── utils/
│       ├── config.py
│       └── paths.py
├── airflow/
│   └── dags/
│       └── lakehouse_bsg_dag.py
├── dbt/
│   └── lakehouse_dbt/
│       ├── dbt_project.yml
│       ├── profiles.yml.example
│       ├── models/
│       │   ├── silver/stg_trips.sql
│       │   └── gold/mart_revenue_daily.sql
│       └── tests/
│           └── schema.yml
└── cloud/
    └── aws/
        ├── athena/
        │   ├── create_bronze_table.sql
        │   ├── create_silver_table.sql
        │   └── create_gold_table.sql
        ├── scripts/
        │   └── sync_to_s3.ps1
        └── iam/
            └── lakehouse_policy.json
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TLC_YEAR` | `2025` | Year of TLC data to download |
| `TLC_MONTH` | `12` | Month (2-digit) of TLC data |
| `TLC_DATASET` | `yellow` | `yellow` or `green` taxi |
| `LAKEHOUSE_DB_PATH` | `data/lakehouse.duckdb` | DuckDB database path |
| `S3_BUCKET` | — | S3 bucket for AWS sync |
| `AWS_REGION` | `us-east-2` | AWS region |

## AWS Deployment (Optional, Free Tier)

1. Create S3 bucket in `us-east-2`
2. Attach `cloud/aws/iam/lakehouse_policy.json` to your IAM user
3. Run `.\cloud\aws\scripts\sync_to_s3.ps1 -Bucket your-bucket`
4. Create Athena database `lakehouse` and run the DDLs in `cloud/aws/athena/`
