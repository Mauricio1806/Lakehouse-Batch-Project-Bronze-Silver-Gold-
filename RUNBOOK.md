# RUNBOOK — lakehouse-b2s2g

Step-by-step execution guide for the NYC TLC Bronze → Silver → Gold pipeline.

---

## Prerequisites

- Docker Desktop running (for Airflow option)
- Python 3.10+ (for local option)
- AWS CLI configured (for S3 sync only)

---

## 1. First-Time Setup

### Clone / enter the project

```bash
cd lakehouse-b2s2g
```

### Create the dbt profiles file

```bash
# Copy the example and adjust the path if needed
cp dbt/lakehouse_dbt/profiles.yml.example dbt/lakehouse_dbt/profiles.yml
```

> The default path `../../data/lakehouse.duckdb` works when running
> `dbt run` from inside `dbt/lakehouse_dbt/`.

---

## 2. Running via Docker (Airflow)

### Start all services

```bash
make up
# or: docker compose up -d
```

Wait ~30 seconds for Airflow to initialise, then open:
**http://localhost:8080** → user: `admin` / password: `admin`

### Trigger the pipeline DAG

In the Airflow UI:
1. Find DAG `lakehouse_bronze_silver_gold`
2. Click the **Run** (▶) button → **Trigger DAG**

Or via CLI:

```bash
docker compose exec airflow-scheduler \
  airflow dags trigger lakehouse_bronze_silver_gold
```

### Monitor

```bash
make logs
# or watch the Airflow UI at http://localhost:8080
```

### Stop

```bash
make down      # stops + removes containers and volumes
# or
docker compose stop   # stops without removing volumes
```

---

## 3. Running Locally (No Docker)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Step 1 — Ingest Bronze

```bash
# Downloads yellow_tripdata_2025-12.parquet → data/raw/
# Then writes partitioned Snappy Parquet → data/bronze/
python -m src.ingest.tlc_download
python -m src.ingest.tlc_to_bronze
# or: make ingest
```

Environment overrides:

```bash
TLC_YEAR=2024 TLC_MONTH=06 python -m src.ingest.tlc_download
```

### Step 2 — Quality Gate (Great Expectations)

```bash
python -m src.ge.ge_run
# or: make ge-check
```

Expected output:
```
[ge_run] PASS: rows=3456789, required_cols_ok=True
```

### Step 3 — dbt Silver model

```bash
cd dbt/lakehouse_dbt
dbt run --select stg_trips --profiles-dir .
# or from root: make dbt-run
```

Output: `data/silver/stg_trips.parquet`

### Step 4 — dbt Gold model

```bash
cd dbt/lakehouse_dbt
dbt run --select mart_revenue_daily --profiles-dir .
```

Output: `data/gold/mart_revenue_daily.parquet`

### Step 5 — dbt Tests

```bash
cd dbt/lakehouse_dbt
dbt test --profiles-dir .
# or from root: make dbt-test
```

### Full pipeline in one command

```bash
make pipeline
```

---

## 4. Querying with DuckDB

```python
import duckdb
con = duckdb.connect("data/lakehouse.duckdb")

# Bronze
con.sql("SELECT COUNT(*) FROM read_parquet('data/bronze/**/*.parquet')").show()

# Silver
con.sql("SELECT * FROM read_parquet('data/silver/stg_trips.parquet') LIMIT 5").show()

# Gold
con.sql("SELECT * FROM read_parquet('data/gold/mart_revenue_daily.parquet') ORDER BY trip_date DESC LIMIT 10").show()
```

---

## 5. AWS Sync (Optional)

### Prerequisites
- AWS CLI installed and configured
- IAM user has policy in `cloud/aws/iam/lakehouse_policy.json`
- S3 bucket created in `us-east-2`

### Sync all layers to S3

```powershell
.\cloud\aws\scripts\sync_to_s3.ps1 -Bucket "your-lakehouse-bucket"

# Dry-run first:
.\cloud\aws\scripts\sync_to_s3.ps1 -Bucket "your-lakehouse-bucket" -DryRun
```

### Create Athena tables

In AWS Athena console, run (in order):

```sql
CREATE DATABASE IF NOT EXISTS lakehouse;
```

Then run each DDL file in `cloud/aws/athena/`, replacing `<YOUR_BUCKET>` with your bucket name:
1. `create_bronze_table.sql`
2. `create_silver_table.sql`
3. `create_gold_table.sql`

Finally, load Bronze partitions:

```sql
MSCK REPAIR TABLE lakehouse.bronze_trips;
```

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| `FileNotFoundError: Raw file not found` | Run `make ingest` first |
| `GE Gate failed: row_count is 0` | Bronze parquet is empty; re-run ingest |
| `GE Gate failed: missing columns` | Wrong dataset type; set `TLC_DATASET=yellow` |
| dbt `Database not found` | Copy `profiles.yml.example` → `profiles.yml` in `dbt/lakehouse_dbt/` |
| Airflow stuck on `airflow-init` | Run `make down && make up` to reset |
| Port 8080 already in use | Change `ports: "8081:8080"` in `docker-compose.yml` |

---

## 7. Re-running for a Different Month

```bash
export TLC_YEAR=2024
export TLC_MONTH=06
make pipeline
```

In Docker, set the environment variables in `.env` before running `make up`.
