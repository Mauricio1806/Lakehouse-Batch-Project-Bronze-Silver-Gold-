-- Athena external table over the Gold S3 layer — per-zone trip aggregates.
-- Region: us-east-1  |  Format: Parquet + Snappy
--
-- NOTE: See create_gold_trips_by_hour_table.sql for the s3 mv note.

CREATE EXTERNAL TABLE IF NOT EXISTS lakehouse.mart_trips_by_location (
    pickup_location_id  INT,
    total_trips         BIGINT,
    total_revenue       DOUBLE,
    avg_fare            DOUBLE,
    avg_distance_miles  DOUBLE,
    avg_tip             DOUBLE,
    active_days         BIGINT
)
STORED AS PARQUET
LOCATION 's3://1lakehousebatch/lakehouse/gold/mart_trips_by_location/'
TBLPROPERTIES ('parquet.compress' = 'SNAPPY');
