# AWS Data Engineering Free Tier — US Macro Lakehouse (Bronze → Silver → Gold)
**BLS (CPI + Unemployment) → S3 (Bronze) → Athena (Analytics)**
Region: **us-east-2**

## Why this project (US-market + enterprise feel)
This portfolio project mirrors common US Data Engineering patterns:
- API ingestion into **S3** (Bronze) with **partitioned** layout (Athena-friendly)
- Clean/conform layer (Silver) and business marts (Gold)
- SQL analytics with **Athena**
- IAM least-privilege policy and runbook
- Designed to be free-tier friendly and scalable by partitioning

## Dataset (official US sources)
Primary source: **Bureau of Labor Statistics (BLS) API**
- CPI-U (All items) — CUUR0000SA0
- Unemployment Rate — LNS14000000

These time series support strong business narratives:
- Inflation trends (MoM/YoY), cost pressure
- Labor market health
- Macro context for retail, logistics, finance, and pricing analytics

## Target Architecture
- **Bronze**: raw JSON objects in S3, partitioned by series_id/year/month
- **Silver** (planned): normalized Parquet (typed schema) in S3
- **Gold** (planned): curated marts (e.g., inflation_yoy, unemployment_trend) in S3
- **Query**: Athena external tables on top of S3 prefixes

## Repo Structure
aws-data-engineering-free-tier/
├── README.md
├── RUNBOOK.md
├── requirements.txt
├── configs/
│   └── config.yaml
├── src/
│   ├── utils/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── s3_paths.py
│   ├── ingestion/
│   │   └── api_to_s3_bronze.py
│   └── transformations/  (planned)
├── analytics/ (planned: athena ddl + queries)
└── iam/
    └── local_user_policy.json

## Setup (Local)
1) Install deps:
   python -m pip install -r requirements.txt

2) Configure AWS CLI:
   aws configure
   Region: us-east-2

3) Create S3 bucket (see RUNBOOK.md) and update:
   configs/config.yaml → aws.s3_bucket

4) Run Bronze ingestion:
   python -m src.ingestion.api_to_s3_bronze

## Bronze Output (S3 Layout)
s3://<bucket>/bronze/bls/
  series_id=CUUR0000SA0/year=2025/month=12/data.json
  series_id=LNS14000000/year=2025/month=12/data.json
  ...

## Next Steps (to complete Silver/Gold + Athena)
- Implement Silver Parquet standard schema
- Implement Gold marts (YoY, moving averages)
- Add Athena DDL + example queries under /analytics
- Add CI workflow and simple unit tests

