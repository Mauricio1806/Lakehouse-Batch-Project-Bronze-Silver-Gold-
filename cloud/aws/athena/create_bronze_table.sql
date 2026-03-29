-- Athena external table over the Bronze S3 layer.
-- Replace <YOUR_BUCKET> with your actual S3 bucket name.
-- Region: us-east-2  |  Format: Parquet + Snappy

CREATE EXTERNAL TABLE IF NOT EXISTS lakehouse.bronze_trips (
    VendorID              BIGINT,
    tpep_pickup_datetime  TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count       DOUBLE,
    trip_distance         DOUBLE,
    RatecodeID            DOUBLE,
    store_and_fwd_flag    STRING,
    PULocationID          BIGINT,
    DOLocationID          BIGINT,
    payment_type          BIGINT,
    fare_amount           DOUBLE,
    extra                 DOUBLE,
    mta_tax               DOUBLE,
    tip_amount            DOUBLE,
    tolls_amount          DOUBLE,
    improvement_surcharge DOUBLE,
    total_amount          DOUBLE,
    congestion_surcharge  DOUBLE,
    Airport_fee           DOUBLE
)
PARTITIONED BY (
    dataset STRING,
    year    STRING,
    month   STRING
)
STORED AS PARQUET
LOCATION 's3://<YOUR_BUCKET>/lakehouse/bronze/'
TBLPROPERTIES ('parquet.compress' = 'SNAPPY');

-- After creating, run to load partitions:
-- MSCK REPAIR TABLE lakehouse.bronze_trips;
