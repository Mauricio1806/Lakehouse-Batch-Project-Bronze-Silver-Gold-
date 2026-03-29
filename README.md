# Lakehouse Batch Pipeline — Bronze → Silver → Gold

**NYC TLC Trip Records · December 2025 · 4.1M trips · $128.7M revenue processed**

> Production-grade Lakehouse architecture using DuckDB, Apache Airflow, dbt, Great Expectations, Grafana, and AWS (S3 + Athena). Fully containerised. Cloud-deployed. Queryable in under 30 seconds from a cold start.

---

## Business Value

This pipeline answers the questions a transportation analytics team needs every morning:

| Question | Gold Mart | Answer (Dec 2025) |
|---|---|---|
| How much revenue did we generate? | `mart_revenue_daily` | **$128.7M total** |
| When is demand highest? | `mart_trips_by_hour` | **Hour 18–19 (6–7 PM)** |
| Which zones generate most value? | `mart_trips_by_location` | **259 active zones tracked** |
| How do customers pay? | `mart_payment_breakdown` | **Credit card dominant** |

The pipeline runs end-to-end in **under 4 minutes** on a laptop inside Docker. The same data is immediately queryable on AWS Athena serverless — no infrastructure to manage.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                          │
│                      Apache Airflow 2.9.3                           │
│              8-task DAG · LocalExecutor · PostgreSQL                │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │         INGESTION (Task 01)         │
          │   NYC TLC API → Raw Parquet files   │
          │   Partitioned: dataset/year/month   │
          └─────────────────┬──────────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │    BRONZE LAYER · Raw Zone         │
          │  data/bronze/dataset=yellow/       │
          │  year=2025/month=12/trips.parquet  │
          │  Schema: 19 raw TLC columns        │
          └─────────────────┬──────────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │   QUALITY GATE (Task 02)            │
          │   Great Expectations via DuckDB     │
          │   6 checks · 98.7% pass rate        │
          │   Blocks pipeline on failure        │
          └─────────────────┬──────────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │    SILVER LAYER · Conformed Zone    │
          │    dbt model: stg_trips             │
          │    • Type-cast all columns          │
          │    • Deduplicate on business key    │
          │    • Filter nulls and negatives     │
          │    data/silver/stg_trips.parquet    │
          │    122.8 MB · 4.1M clean trips      │
          └─────────────────┬──────────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │     GOLD LAYER · Business Zone      │
          │     4 dbt analytical mart models    │
          │                                     │
          │  mart_revenue_daily      (32 rows)  │
          │  mart_trips_by_hour      (24 rows)  │
          │  mart_trips_by_location (259 rows)  │
          │  mart_payment_breakdown   (5 rows)  │
          └──────┬──────────────────────┬───────┘
                 │                      │
    ┌────────────▼──────┐   ┌───────────▼──────────┐
    │  LOCAL ANALYTICS  │   │    AWS CLOUD LAYER    │
    │  DuckDB engine    │   │  S3: 1lakehousebatch  │
    │  HTML report      │   │  Athena: 6 ext tables │
    │  Grafana dashboard│   │  IAM: least-privilege │
    │  Data profiler    │   │  Region: us-east-1    │
    └───────────────────┘   └──────────────────────┘
```

---

## Pipeline Results (December 2025)

| Metric | Value |
|---|---|
| Raw trips ingested | 4,105,758 |
| Trips after quality gate | ~4.1M (98.7% pass rate) |
| Date range | Dec 1 – Dec 31, 2025 |
| Total Revenue | **$128,671,679** |
| Total Base Fare | ~$98.4M |
| Average Fare per Trip | **$22.44** |
| Average Passengers | 1.39 |
| Peak Day | **Dec 13** — 176,815 trips |
| Slowest Day | Dec 25 (Christmas) — 65,996 trips |
| Bronze Parquet size | ~480 MB (raw) |
| Silver Parquet size | **122.8 MB** (Snappy compressed) |
| Gold Parquet sizes | < 15 KB total (pre-aggregated) |
| dbt models | 5 (1 Silver + 4 Gold) |
| dbt tests passing | 24 / 24 |
| End-to-end pipeline runtime | < 4 minutes |

---

## Technology Stack

| Layer | Tool | Version | Purpose |
|---|---|---|---|
| Orchestration | Apache Airflow | 2.9.3 | DAG scheduling, task monitoring |
| Storage format | Apache Parquet + Snappy | — | Columnar compressed storage |
| Query engine | DuckDB | 1.1.3 | Local analytical engine, Parquet reader |
| Transformations | dbt-duckdb | 1.8.3 | SQL transformations + data tests |
| Quality gate | Great Expectations (DuckDB) | custom | Schema + business rule validation |
| Visualisation | Grafana OSS | 10.4.2 | Live dashboard, Infinity datasource |
| Cloud storage | Amazon S3 | — | Durable lake storage (us-east-1) |
| Cloud query | Amazon Athena | — | Serverless SQL on S3 Parquet |
| Identity | AWS IAM | — | Least-privilege access policy |
| Containerisation | Docker + Compose | — | Fully reproducible environment |
| Language | Python 3.11 | — | Ingestion, GE, analytics scripts |

---

## Repository Structure

```
lakehouse-b2s2g/
│
├── Dockerfile                        # Custom Airflow image with all deps pre-baked
├── docker-compose.yml                # Airflow + Postgres + Grafana + Nginx
├── requirements.txt
│
├── airflow/
│   └── dags/
│       └── lakehouse_bsg_dag.py      # 8-task DAG definition
│
├── src/
│   ├── ingest/
│   │   ├── tlc_download.py           # Downloads TLC Parquet from official API
│   │   └── tlc_to_bronze.py          # Writes partitioned Bronze Parquet
│   ├── ge/
│   │   └── ge_run.py                 # DuckDB-based quality gate (6 checks)
│   └── analytics/
│       ├── profile.py                # Cross-layer data profiler → .txt report
│       ├── report.py                 # Plotly HTML executive report
│       └── grafana_export.py         # Gold → JSON for Grafana Infinity datasource
│
├── dbt/lakehouse_dbt/
│   ├── profiles.yml                  # DuckDB connection (env_var LAKEHOUSE_DB_PATH)
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── silver/stg_trips.sql      # Conformed Silver model
│   │   └── gold/
│   │       ├── mart_revenue_daily.sql
│   │       ├── mart_trips_by_hour.sql
│   │       ├── mart_trips_by_location.sql
│   │       └── mart_payment_breakdown.sql
│   └── tests/schema.yml              # 24 data quality tests
│
├── grafana/
│   ├── nginx.conf                    # Serves JSON exports for Infinity datasource
│   ├── data/                         # Auto-populated by grafana_export.py
│   │   ├── revenue_daily.json
│   │   ├── trips_by_hour.json
│   │   ├── trips_by_location.json
│   │   ├── payment_breakdown.json
│   │   └── summary.json
│   ├── provisioning/
│   │   ├── datasources/infinity.yml  # Auto-provisions Infinity datasource
│   │   └── dashboards/provider.yml   # Dashboard file provider
│   └── dashboards/
│       └── lakehouse_dashboard.json  # 10-panel NYC TLC analytics dashboard
│
├── data/
│   ├── bronze/                       # Partitioned raw Parquet (dataset/year/month)
│   ├── silver/                       # stg_trips.parquet (122.8 MB)
│   ├── gold/                         # 4 mart Parquet files
│   └── lakehouse.duckdb              # DuckDB analytical database
│
├── reports/                          # Generated HTML reports + profiler text
│
└── cloud/aws/
    ├── iam/lakehouse_policy.json     # IAM policy: S3 + Athena + Glue (read)
    ├── athena/                       # 6 CREATE EXTERNAL TABLE DDL files
    └── scripts/
        ├── sync_to_s3.ps1            # Sync Bronze/Silver/Gold → S3
        └── setup_athena.ps1          # Create all Athena tables end-to-end
```

---

## Quick Start

### Prerequisites
- Docker Desktop (Windows / Mac / Linux)
- AWS CLI configured with a profile that has the `lakehouse_policy.json` permissions
- ~5 GB free disk space

### 1. Clone and start

```bash
git clone https://github.com/Mauricio1806/Lakehouse-Batch-Project-Bronze-Silver-Gold-.git
cd lakehouse-b2s2g
docker compose up -d --build
```

### 2. Wait for Airflow to initialise (~30 seconds)

```bash
docker compose logs airflow-init --follow
# Wait for: "Admin user admin created"
```

### 3. Run the full pipeline

Open **http://localhost:8080** (admin / admin) → Trigger the `lakehouse_bronze_silver_gold` DAG.

Or via CLI:
```bash
docker exec lakehouse-b2s2g-airflow-scheduler-1 \
  airflow dags trigger lakehouse_bronze_silver_gold
```

### 4. Open Grafana dashboard

Open **http://localhost:3000** (admin / lakehouse) → The *NYC TLC Lakehouse — Executive Analytics* dashboard loads automatically.

> The Infinity plugin installs on first Grafana start (~60 seconds). If panels show "Datasource not found", wait 60 s and refresh.

### 5. Deploy to AWS (optional)

```powershell
# Sync all layers to S3
.\cloud\aws\scripts\sync_to_s3.ps1 -Profile "your-aws-profile"

# Create all Athena tables
.\cloud\aws\scripts\setup_athena.ps1 -Profile "your-aws-profile"
```

---

## Airflow DAG — 8-Task Pipeline

```
01_ingest_bronze
      │
02_ge_quality_gate          ← Blocks on failure
      │
03_dbt_silver
      │
04_dbt_gold                 ← 4 marts run in parallel
      │
05_dbt_tests                ← 24 tests must pass
      │
06_data_profile             → reports/profile_*.txt
      │
07_analytics_report         → reports/lakehouse_report_*.html
      │
08_grafana_export           → grafana/data/*.json
```

---

## Grafana Dashboard — 10 Panels

Access at **http://localhost:3000** (auto-provisioned, no manual setup needed).

| Panel | Type | Data Source |
|---|---|---|
| Total Revenue KPI | Stat | `revenue_daily.json` |
| Total Trips KPI | Stat | `revenue_daily.json` |
| Avg Daily Revenue KPI | Stat | `revenue_daily.json` |
| Avg Passengers KPI | Stat | `revenue_daily.json` |
| Daily Revenue Trend | Time Series | `revenue_daily.json` |
| Trips by Hour of Day | Bar Chart | `trips_by_hour.json` |
| Payment Method Distribution | Donut | `payment_breakdown.json` |
| Revenue by Payment Method | Horizontal Bar | `payment_breakdown.json` |
| Top 15 Zones by Revenue | Horizontal Bar | `trips_by_location.json` |
| Daily Revenue Detail | Table + Footer | `revenue_daily.json` |

---

## AWS Cloud Architecture

```
                          us-east-1
                    ┌─────────────────────┐
                    │   Amazon S3         │
                    │   1lakehousebatch   │
                    │                     │
                    │ lakehouse/          │
                    │   bronze/           │  ← partitioned Parquet
                    │   silver/           │  ← stg_trips.parquet
                    │   gold/             │  ← 4 mart sub-prefixes
                    └──────────┬──────────┘
                               │ LOCATION
                    ┌──────────▼──────────┐
                    │   Amazon Athena     │
                    │   DB: lakehouse     │
                    │                     │
                    │  bronze_trips       │  ← partitioned, MSCK REPAIR
                    │  silver_trips       │
                    │  mart_revenue_daily │
                    │  mart_trips_by_hour │
                    │  mart_trips_by_loc  │
                    │  mart_payment_brkdn │
                    └─────────────────────┘
```

**IAM Policy** (`cloud/aws/iam/lakehouse_policy.json`): scoped to `1lakehousebatch` bucket only. Grants S3 read/write/list, Athena query execution, Glue catalog read, and workgroup management.

---

## Data Quality — Great Expectations Gate

The pipeline enforces 6 DuckDB-native checks before Silver transformation:

| Check | Rule |
|---|---|
| Row count | > 0 rows in Bronze |
| No nulls | `tpep_pickup_datetime`, `fare_amount` not null |
| Positive fares | `fare_amount > 0` |
| Valid distances | `trip_distance > 0` |
| Date range | All trips within expected month |
| Payment types | `payment_type IN (1,2,3,4,5,6)` |

**Result**: 98.7% of December 2025 trips pass all checks.

---

## dbt Tests — 24 Automated Checks

```bash
# Run all tests
dbt test --project-dir dbt/lakehouse_dbt --profiles-dir dbt/lakehouse_dbt
# 24 passed, 0 failed
```

Tests cover: `unique`, `not_null`, `accepted_values`, and `relationships` on all 5 models.

---

## Sample Athena Queries

```sql
-- Daily revenue trend
SELECT trip_date, total_trips, total_revenue, avg_distance_miles
FROM lakehouse.mart_revenue_daily
ORDER BY trip_date;

-- Peak demand by hour (Christmas week)
SELECT hour_of_day, total_trips, avg_fare
FROM lakehouse.mart_trips_by_hour
ORDER BY total_trips DESC
LIMIT 5;

-- Payment method market share
SELECT payment_method, total_trips, pct_of_trips, pct_of_revenue
FROM lakehouse.mart_payment_breakdown
ORDER BY total_trips DESC;

-- Top revenue zones
SELECT pickup_location_id, total_revenue, avg_fare, total_trips
FROM lakehouse.mart_trips_by_location
ORDER BY total_revenue DESC
LIMIT 10;
```

---

## Why This Architecture

| Design Decision | Rationale |
|---|---|
| DuckDB instead of Spark | Processes 4M rows in seconds locally with zero infrastructure overhead |
| External dbt materialization | Gold marts are Parquet files — portable to S3/Athena without schema changes |
| GE as a pipeline gate | Blocks corrupt data from reaching Silver; errors are explicit not silent |
| Airflow LocalExecutor | Full Airflow semantics (retries, alerting, lineage) without the Celery/K8s overhead |
| Parquet + Snappy | ~75% size reduction vs CSV; columnar pushdown for Athena cost savings |
| Grafana Infinity datasource | Reads JSON files served by nginx — no database connection needed, works offline |
| Per-model S3 sub-prefixes | Prevents Athena schema conflicts when multiple marts share a top-level prefix |

---

## Roadmap

- [ ] Incremental loads (append-only Bronze with dedup at Silver)
- [ ] dbt incremental models with DuckDB microbatch
- [ ] Grafana alerting (revenue drop > 20% day-over-day)
- [ ] CI/CD pipeline (GitHub Actions: dbt test + GE on every PR)
- [ ] Multi-month backfill (2024–2025 full year)
- [ ] AWS Glue job equivalent for cloud-native transformation
- [ ] Streaming extension (Kinesis → Bronze hot path)

---

*Data Engineering Portfolio Project — NYC TLC Lakehouse Batch Pipeline*
*Stack: DuckDB · Airflow · dbt · Great Expectations · Grafana · AWS S3 · Athena*
