# RUNBOOK (AWS Free Tier) — us-east-2

## 1) Create S3 Bucket (us-east-2)
- S3 → Create bucket
- Region: **us-east-2**
- Block Public Access: ON (default)
- Encryption: ON (SSE-S3)

Bucket name suggestion:
- mauricio-us-east-2-de-lakehouse

## 2) Create IAM User for local dev
IAM → Users → Create user
- Access key: YES (Programmatic)
- Attach policy: use iam/local_user_policy.json (create as inline policy)

## 3) Configure AWS CLI (local)
Install AWS CLI v2, then:
aws configure
- AWS Access Key ID: ...
- AWS Secret Access Key: ...
- Default region name: us-east-2
- Default output format: json

Test:
aws sts get-caller-identity

## 4) Update config.yaml
Set:
aws.s3_bucket: <your-bucket-name>

## 5) Run ingestion (BLS → S3 Bronze)
python -m src.ingestion.api_to_s3_bronze

## 6) Validate objects in S3
S3 → bucket → bronze/bls/series_id=.../year=.../month=...

Next steps:
- Create Athena DB + external tables (see /analytics)
- Implement silver/gold parquet transforms into S3
