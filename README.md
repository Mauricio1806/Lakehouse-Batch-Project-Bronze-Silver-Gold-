# Lakehouse Batch Pipeline — Bronze → Silver → Gold

**4,105,758 trips · $128.7M revenue · December 2025 · NYC TLC**

This pipeline ingests NYC Taxi & Limousine Commission trip records, enforces data quality, transforms raw operational data into business-ready analytical marts, and delivers results through a live Grafana dashboard and AWS Athena — all orchestrated by Apache Airflow and running in a single `docker compose up`.

---

## Live Systems

| System | URL | Credentials |
|---|---|---|
| Grafana Dashboard | [http://localhost:3000/d/lakehouse-nyc-tlc](http://localhost:3000/d/lakehouse-nyc-tlc) | admin / lakehouse |
| Airflow | [http://localhost:8080](http://localhost:8080) | admin / admin |
| S3 Lake | [s3://1lakehousebatch — us-east-1](https://s3.console.aws.amazon.com/s3/buckets/1lakehousebatch?region=us-east-1&tab=objects) | AWS Console |
| Athena | [lakehouse database — us-east-1](https://us-east-1.console.aws.amazon.com/athena/home?region=us-east-1#/query-editor) | AWS Console |
| GitHub | [Lakehouse-Batch-Project-Bronze-Silver-Gold-](https://github.com/Mauricio1806/Lakehouse-Batch-Project-Bronze-Silver-Gold-) | Public |

---

## What This Delivers

The pipeline runs eight tasks end-to-end and produces four analytical Gold marts, a live dashboard, and an HTML executive report. Every run is idempotent — re-triggering the DAG overwrites and refreshes all outputs.

**December 2025 results:**

| Mart | Rows | Business Content |
|---|---|---|
| `mart_revenue_daily` | 32 | Revenue, fares, tips, distance by calendar day |
| `mart_trips_by_hour` | 24 | Demand pattern and fare efficiency by hour of day |
| `mart_trips_by_location` | 259 | Revenue concentration by TLC pickup zone |
| `mart_payment_breakdown` | 5 | Market share and revenue split by payment type |

Peak day was **December 13** with 176,815 trips. Christmas Day was the slowest at 65,996 — a 63% drop that the daily mart captures cleanly. Average fare held at **$22.44** throughout the month, with credit card trips generating higher tips than cash on every single day in the dataset.

---

## Architecture

```
NYC TLC API (Parquet)
        │
        ▼
  ┌─────────────┐
  │   BRONZE    │  Raw partitioned Parquet  ·  dataset=yellow/year=2025/month=12
  │             │  19 columns · ~480 MB uncompressed
  └──────┬──────┘
         │  Great Expectations gate — 6 checks, 98.7% pass rate
  ┌──────▼──────┐
  │   SILVER    │  Conformed Parquet  ·  stg_trips.parquet  ·  122.8 MB Snappy
  │             │  Deduped, cast, nulls filtered, business key validated
  └──────┬──────┘
         │  dbt external materialisation — 4 models run in parallel
  ┌──────▼──────────────────────────────────────────┐
  │                    GOLD                          │
  │  mart_revenue_daily  ·  mart_trips_by_hour       │
  │  mart_trips_by_location  ·  mart_payment_brkdn   │
  │  Pre-aggregated Parquet — sub-second Athena scan │
  └──────┬──────────────────┬───────────────────────┘
         │                  │
  ┌──────▼──────┐    ┌──────▼──────────────┐
  │   Grafana   │    │   Amazon S3 + Athena │
  │  10 panels  │    │   6 external tables  │
  │  localhost  │    │   us-east-1          │
  └─────────────┘    └─────────────────────┘
```

The Bronze-Silver-Gold separation is not cosmetic. Bronze is append-only, never mutated — it preserves the source record exactly as received from the TLC API. Silver enforces the schema contract: any column that cannot be cast to its expected type or fails a null check is dropped before it ever reaches a mart. Gold is pure aggregation; it has no joins and no business logic that wasn't already validated in Silver. That layering is what allows Athena to scan Gold in milliseconds and never touch the 480 MB Bronze file.

---

## Data Quality

Six DuckDB-native checks run as a blocking gate between Bronze and Silver:

- Row presence — Bronze must contain data before Silver runs
- Null enforcement on `tpep_pickup_datetime` and `fare_amount`
- Positive fare and trip distance validation
- Date range containment within the expected month
- Payment type enum validation (`1–6` only)

**98.7%** of December trips cleared all six checks. The 1.3% that failed — predominantly zero-distance airport surcharge records — were silently dropped at Silver, not surfaced as errors. A data contract this explicit means downstream analysts can trust that every row in a Gold mart passed a documented quality assertion.

---

## Design Decisions

**DuckDB over Spark.** For a single-month batch of 4M rows, the operational cost of Spark — cluster provisioning, serialisation overhead, JVM memory tuning — produces no benefit. DuckDB reads the 122 MB Silver Parquet in 7 seconds and runs all four Gold models in parallel in under 10 seconds total. The architectural pattern is identical to a Spark pipeline; only the engine is different, and the engine is the correct one for the data volume.

**dbt external materialisation.** Gold models write directly to Parquet files at defined paths. This means the same SQL that runs in Docker also runs against S3 via Athena — no schema migration, no `COPY INTO`, no intermediate staging table. The Gold marts are files first; databases are just an index over them.

**Per-model S3 sub-prefixes for Gold.** Each Gold mart lives at `gold/<model>/<model>.parquet`. A single `gold/` LOCATION in Athena would force every table to scan files with incompatible schemas. The sub-prefix layout gives each Athena external table a clean, isolated LOCATION with exactly one Parquet file behind it.

**Grafana Infinity datasource over a live DB connection.** The Gold marts are already tiny (< 15 KB combined). Exporting them to JSON at pipeline end and serving via nginx decouples the dashboard from the database entirely — Grafana never holds a DuckDB connection, never blocks a pipeline run, and renders panels from static files that survive a database restart. The tradeoff is that dashboard data is as fresh as the last DAG run, which is acceptable for a batch pipeline.

---

## Gold Layer — S3 Layout

```
s3://1lakehousebatch/
└── lakehouse/
    ├── bronze/
    │   └── dataset=yellow/year=2025/month=12/trips.parquet
    ├── silver/
    │   └── stg_trips.parquet                               (122.8 MB)
    └── gold/
        ├── mart_revenue_daily/mart_revenue_daily.parquet   (2.4 KB)
        ├── mart_trips_by_hour/mart_trips_by_hour.parquet   (2.0 KB)
        ├── mart_trips_by_location/...parquet               (9.3 KB)
        └── mart_payment_breakdown/...parquet               (1.3 KB)
```

---

## Athena — Sample Queries

```sql
-- Revenue trend with day-over-day change
SELECT
    trip_date,
    total_trips,
    total_revenue,
    ROUND(total_revenue - LAG(total_revenue) OVER (ORDER BY trip_date), 2) AS revenue_delta
FROM lakehouse.mart_revenue_daily
ORDER BY trip_date;

-- Hour-of-day demand vs fare efficiency
SELECT
    hour_of_day,
    total_trips,
    avg_fare,
    ROUND(total_revenue / NULLIF(total_trips, 0), 2) AS revenue_per_trip
FROM lakehouse.mart_trips_by_hour
ORDER BY total_trips DESC;

-- Payment channel market share
SELECT
    payment_method,
    total_trips,
    pct_of_trips,
    pct_of_revenue,
    avg_tip
FROM lakehouse.mart_payment_breakdown
ORDER BY total_trips DESC;
```

---

## Repository

```
lakehouse-b2s2g/
├── Dockerfile                             Custom Airflow 2.9.3 image, all deps pre-baked
├── docker-compose.yml                     Airflow · Postgres · Grafana · Nginx
├── airflow/dags/lakehouse_bsg_dag.py      8-task DAG
├── src/
│   ├── ingest/tlc_to_bronze.py            TLC API → partitioned Bronze Parquet
│   ├── ge/ge_run.py                       DuckDB quality gate
│   └── analytics/
│       ├── grafana_export.py              Gold Parquet → JSON for Grafana
│       ├── report.py                      Plotly HTML executive report
│       └── profile.py                     Cross-layer data profiler
├── dbt/lakehouse_dbt/
│   ├── models/silver/stg_trips.sql
│   └── models/gold/                       4 analytical mart models
├── grafana/
│   ├── dashboards/lakehouse_dashboard.json
│   ├── provisioning/                      Auto-provisioned datasource + dashboard
│   └── data/                             JSON exports (populated at pipeline end)
└── cloud/aws/
    ├── iam/lakehouse_policy.json          Least-privilege: S3 + Athena + Glue read
    ├── athena/                            6 CREATE EXTERNAL TABLE DDL files
    └── scripts/
        ├── sync_to_s3.ps1
        └── setup_athena.ps1
```

---

*NYC TLC Lakehouse · DuckDB · Airflow 2.9.3 · dbt-duckdb 1.8.3 · Grafana 10.4.2 · S3 · Athena · us-east-1*
