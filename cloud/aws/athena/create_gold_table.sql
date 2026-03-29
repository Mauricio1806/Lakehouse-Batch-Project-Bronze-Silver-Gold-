-- Athena external table over the Gold S3 layer.
-- Replace <YOUR_BUCKET> with your actual S3 bucket name.
-- Region: us-east-2  |  Format: Parquet + Snappy

CREATE EXTERNAL TABLE IF NOT EXISTS lakehouse.mart_revenue_daily (
    trip_date           DATE,
    total_trips         BIGINT,
    total_fare          DOUBLE,
    total_tips          DOUBLE,
    total_revenue       DOUBLE,
    avg_distance_miles  DOUBLE,
    avg_passengers      DOUBLE
)
STORED AS PARQUET
LOCATION 's3://<YOUR_BUCKET>/lakehouse/gold/'
TBLPROPERTIES ('parquet.compress' = 'SNAPPY');
