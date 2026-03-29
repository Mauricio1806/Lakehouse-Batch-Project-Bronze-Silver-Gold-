-- Athena external table over the Gold S3 layer — payment method breakdown.
-- Region: us-east-1  |  Format: Parquet + Snappy
--
-- NOTE: See create_gold_trips_by_hour_table.sql for the s3 mv note.

CREATE EXTERNAL TABLE IF NOT EXISTS lakehouse.mart_payment_breakdown (
    payment_type    INT,
    payment_method  STRING,
    total_trips     BIGINT,
    total_revenue   DOUBLE,
    avg_fare        DOUBLE,
    avg_tip         DOUBLE,
    pct_of_trips    DOUBLE,
    pct_of_revenue  DOUBLE
)
STORED AS PARQUET
LOCATION 's3://1lakehousebatch/lakehouse/gold/mart_payment_breakdown/'
TBLPROPERTIES ('parquet.compress' = 'SNAPPY');
