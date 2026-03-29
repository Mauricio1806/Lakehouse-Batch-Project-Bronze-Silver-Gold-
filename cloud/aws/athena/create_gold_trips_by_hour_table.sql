-- Athena external table over the Gold S3 layer — hourly trip aggregates.
-- Region: us-east-1  |  Format: Parquet + Snappy
--
-- NOTE: The Gold layer is a flat prefix; each model maps to its own
--       single Parquet file.  Athena reads all Parquet files under LOCATION,
--       so each model gets its own sub-prefix created by the S3 sync layout.
--       If files were synced flat (all under lakehouse/gold/), separate them
--       with: aws s3 mv s3://1lakehousebatch/lakehouse/gold/mart_trips_by_hour.parquet
--                        s3://1lakehousebatch/lakehouse/gold/mart_trips_by_hour/mart_trips_by_hour.parquet

CREATE EXTERNAL TABLE IF NOT EXISTS lakehouse.mart_trips_by_hour (
    hour_of_day         INT,
    total_trips         BIGINT,
    total_revenue       DOUBLE,
    avg_fare            DOUBLE,
    avg_tip             DOUBLE,
    avg_distance_miles  DOUBLE,
    avg_passengers      DOUBLE
)
STORED AS PARQUET
LOCATION 's3://1lakehousebatch/lakehouse/gold/mart_trips_by_hour/'
TBLPROPERTIES ('parquet.compress' = 'SNAPPY');
