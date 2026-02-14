# Lakehouse Batch Project (Bronze → Silver → Gold)
**DuckDB + Parquet + Airflow + dbt + Great Expectations**

A fully reproducible end-to-end Data Engineering project implementing a Lakehouse architecture with clear Bronze, Silver, and Gold layers.  
Designed for portfolio demonstration and direct cloud mapping to Azure and AWS environments.

---

# Project Objective

This project demonstrates:

- Lakehouse architecture (Bronze / Silver / Gold layers)
- Partitioned Parquet data lake storage
- Orchestration with Apache Airflow
- Transformations and testing with dbt
- Data Quality Gate using Great Expectations
- Reproducible local setup via Docker + Make
- Direct architectural mapping to Azure and AWS

---

# Real-World Data Source

**NYC Taxi & Limousine Commission (TLC) Trip Record Data**

Official public dataset published by NYC TLC.

Why this dataset:
- Operational transactional data
- Real-world schema complexity
- Monthly partitioning structure
- High data volume
- Official documentation and data dictionary
- Available via AWS Open Data Registry (cloud-aligned)

This makes it production-relevant and suitable for enterprise data engineering portfolios.

---

# Architecture Overview

            +-------------------------+
            | NYC TLC Trip Records    |
            | (CSV / Parquet monthly) |
            +------------+------------+
                         |
                         v
                (01) Ingestion
                         |
                         v
        🥉 Bronze (Raw Parquet + partitioned)
                         |
                         v
    (02) Great Expectations Quality Gate
                         |
                         v
       (03) dbt run → 🥈 Silver (conformed)
                         |
                         v
       (04) dbt run → 🥇 Gold (data marts)
                         |
                         v
            DuckDB (lakehouse.duckdb)

---

# Tech Stack (Local Environment)

- Apache Airflow (orchestration)
- DuckDB (analytical engine)
- Parquet + Snappy (data lake format)
- dbt-duckdb (transformations & tests)
- Great Expectations (data quality validation)
- Docker + Make (reproducibility)

---

# Quick Start

## 1. Start the environment

```bash
make up
http://localhost:8080
username: admin
password: admin
make run-local
make logs

Pipeline Stages
1. Ingestion

Downloads a monthly TLC dataset and stores it in Bronze as partitioned Parquet files.

2. Data Quality Gate

Great Expectations validates:

Non-null primary identifiers

Accepted value ranges

Basic schema integrity

Pipeline execution stops if validation fails.

3. Silver Layer (dbt)

Type casting

Schema normalization

Data cleaning

4. Gold Layer (dbt)

Business-ready aggregations

Daily revenue mart

Analytical metrics
lakehouse-b2s2g/
  README.md
  Makefile
  docker-compose.yml
  requirements.txt

  data/
    bronze/
    silver/
    gold/

  src/
    ingest/
      tlc_download.py
      tlc_to_bronze.py
    ge_run.py

  airflow/
    dags/
      lakehouse_bsg_dag.py

  dbt/
    lakehouse_dbt/
      dbt_project.yml
      profiles.yml.example
      models/
        silver/
          stg_trips.sql
        gold/
          mart_revenue_daily.sql
      tests/
        schema.yml

  cloud/
    azure/
      README.md
      mapping.md
    aws/
      README.md
      mapping.md

Outputs

Bronze raw files: data/bronze/

DuckDB database file: data/lakehouse.duckdb

Gold mart example: mart_revenue_daily

Outputs

Bronze raw files: data/bronze/

DuckDB database file: data/lakehouse.duckdb

Gold mart example: mart_revenue_daily

Cloud Architecture Mapping
Azure Equivalent
Local Component	Azure Equivalent
Local Parquet	ADLS Gen2
Airflow	Azure Data Factory
dbt + GE	Databricks Job / Fabric Pipeline
DuckDB	Synapse / Fabric Warehouse

Details available in:

cloud/azure/README.md

AWS Equivalent
Local Component	AWS Equivalent
Local Parquet	Amazon S3
Airflow	MWAA (Managed Airflow)
dbt + GE	AWS Glue Job
DuckDB	Redshift or Athena

Details available in:

cloud/aws/README.md

Why This Project Is Portfolio-Ready

Fully reproducible via Docker

Clear Lakehouse layer separation

Production-like data validation gate

Tested transformation logic

Cloud-ready architectural thinking

Real-world public dataset

Enterprise documentation style

Next Steps (Planned Extensions)

Incremental load support

Data lineage visualization

CI pipeline (GitHub Actions)

Cost-aware cloud deployment blueprint

Streaming extension (Kafka + ClickHouse)

Author

Data Engineering Portfolio Project
Focused on Azure & AWS modern data stack alignment.
