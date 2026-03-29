-- Athena external table over the Silver S3 layer.
-- Replace <YOUR_BUCKET> with your actual S3 bucket name.
-- Region: us-east-1  |  Format: Parquet + Snappy

CREATE EXTERNAL TABLE IF NOT EXISTS lakehouse.silver_trips (
    pickup_datetime     TIMESTAMP,
    dropoff_datetime    TIMESTAMP,
    passenger_count     INT,
    trip_distance       DOUBLE,
    pickup_location_id  INT,
    dropoff_location_id INT,
    fare_amount         DOUBLE,
    tip_amount          DOUBLE,
    total_amount        DOUBLE,
    payment_type        INT
)
STORED AS PARQUET
LOCATION 's3://1lakehousebatch/lakehouse/silver/'
TBLPROPERTIES ('parquet.compress' = 'SNAPPY');
