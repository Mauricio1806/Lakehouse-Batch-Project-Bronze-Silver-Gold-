# Lakehouse Batch Project (Bronze → Silver → Gold)
DuckDB + Parquet + Airflow + dbt + Great Expectations  
AWS-Ready Architecture (S3 + Athena | us-east-2 | Free Tier Safe)

---

## Overview

This project implements a production-grade Lakehouse Batch Architecture using clear Bronze, Silver, and Gold layers.

It is designed to:

- Demonstrate real-world Data Engineering architecture
- Be fully reproducible locally (Docker-based execution)
- Map directly to AWS cloud infrastructure
- Follow enterprise-grade structuring patterns
- Remain Free Tier safe while still using real AWS services
- Be portfolio-ready for the US Data Engineering market

---

## Project Objectives

This repository demonstrates:

- Layered Lakehouse architecture (Bronze / Silver / Gold)
- Partitioned Parquet data lake structure
- Orchestration using Apache Airflow
- Transformations and testing with dbt
- Data Quality enforcement using Great Expectations
- Analytical execution using DuckDB
- Cloud-aligned AWS architecture
- Versioned SQL and infrastructure logic
- Clear separation of compute, storage, and transformation layers

---

## Real-World Dataset

NYC Taxi & Limousine Commission (TLC) Trip Record Data

Why TLC:

- Operational transactional data
- Real production-like schema complexity
- Monthly partitioned dataset
- Public and well-documented
- Widely used in enterprise Data Engineering environments
- Cloud-aligned distribution patterns

---

## Architecture – Logical Flow

NYC TLC Data (Monthly Files)
        │
        ▼
(01) Ingestion
        │
        ▼
Bronze Layer – Raw partitioned Parquet files
        │
        ▼
(02) Great Expectations – Data Quality Validation Gate
        │
        ▼
(03) dbt Transformations → Silver Layer (Conformed Data)
        │
        ▼
(04) dbt Aggregations → Gold Layer (Business Marts)
        │
        ▼
DuckDB Analytical Engine (data/lakehouse.duckdb)

---

## Local Technology Stack

- Apache Airflow (Orchestration)
- DuckDB (Lakehouse analytical engine)
- Parquet + Snappy (Columnar storage format)
- dbt-duckdb (Transformations and testing)
- Great Expectations (Data validation layer)
- Docker + Make (Reproducible environment)

---

## AWS Cloud Alignment (us-east-2)

This project maps directly to AWS architecture while remaining Free Tier safe.

Local to AWS mapping:

Local Parquet → Amazon S3  
DuckDB → Athena (serverless querying)  
Airflow → MWAA (conceptual mapping, not deployed in Phase 1)  
dbt + GE → AWS Glue Jobs (optional Phase 2)  

AWS Services Used in Phase 1:

- Amazon S3 (Bronze/Silver/Gold lake storage)
- Amazon Athena (Serverless SQL on Gold layer)
- AWS IAM (Least privilege policies)

Free Tier Guardrails:

- Region: us-east-2
- $1 budget alert configured
- No always-on services
- Manual execution only
- Athena queries limited to Gold partitions

---

## Repository Structure

lakehouse-b2s2g/

README.md  
RUNBOOK.md  
Makefile  
docker-compose.yml  
requirements.txt  

data/  
  bronze/  
  silver/  
  gold/  
  lakehouse.duckdb  

src/  
  ingest/  
    tlc_download.py  
    tlc_to_bronze.py  
  ge/  
    ge_run.py  
  utils/  
    config.py  
    paths.py  

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
  aws/  
    README.md  
    athena/  
      setup.sql  
      gold_tables.sql  
      queries.sql  
    scripts/  
      sync_to_s3.ps1  
    iam/  
      local_user_policy.json  
      glue_role_policy.json  

  azure/  
    README.md  
    mapping.md  

---

## Expected Outputs

Local Outputs:

- Bronze raw files in data/bronze/
- Silver conformed datasets in data/silver/
- Gold analytical marts in data/gold/
- DuckDB database file in data/lakehouse.duckdb
- Gold example mart: mart_revenue_daily

AWS Outputs (Phase 1):

- S3 lake storage with partitioned structure
- Athena external tables pointing to Gold layer
- Queryable analytics in AWS console

---

## Why This Project Is Portfolio-Grade

- Clear Lakehouse layer separation
- Production-style data validation gate
- Tested transformation logic
- Analytics-as-code (Athena SQL versioned)
- Least-privilege IAM structure
- Reproducible environment
- Cloud-ready architecture
- Enterprise documentation style
- US-market aligned stack (Airflow + dbt + AWS)

---

## Roadmap (Planned Extensions)

- Incremental load implementation
- Glue-based cloud transformation jobs
- Data lineage visualization
- CI pipeline (dbt + GE automated checks)
- Cost-aware infrastructure blueprint
- Streaming extension (separate project)

---

Author:  
Data Engineering Portfolio Project  
Focused on AWS and Azure modern data stack alignment.
