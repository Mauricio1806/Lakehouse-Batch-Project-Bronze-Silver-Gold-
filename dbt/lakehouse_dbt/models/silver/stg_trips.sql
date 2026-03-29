{{
    config(
        materialized  = 'external',
        location      = '/opt/airflow/data/silver/stg_trips.parquet',
        format        = 'parquet',
        options       = {'codec': 'snappy'}
    )
}}

WITH source AS (
    SELECT *
    FROM read_parquet('/opt/airflow/data/bronze/**/*.parquet')
),

deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY
                tpep_pickup_datetime,
                tpep_dropoff_datetime,
                PULocationID,
                DOLocationID,
                fare_amount
            ORDER BY tpep_pickup_datetime
        ) AS _rn
    FROM source
    WHERE tpep_pickup_datetime IS NOT NULL
      AND tpep_dropoff_datetime IS NOT NULL
      AND fare_amount          > 0
      AND trip_distance        > 0
)

SELECT
    CAST(tpep_pickup_datetime  AS TIMESTAMP) AS pickup_datetime,
    CAST(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_datetime,
    CAST(passenger_count       AS INTEGER)   AS passenger_count,
    CAST(trip_distance         AS DOUBLE)    AS trip_distance,
    CAST(PULocationID          AS INTEGER)   AS pickup_location_id,
    CAST(DOLocationID          AS INTEGER)   AS dropoff_location_id,
    CAST(fare_amount           AS DOUBLE)    AS fare_amount,
    CAST(tip_amount            AS DOUBLE)    AS tip_amount,
    CAST(total_amount          AS DOUBLE)    AS total_amount,
    CAST(payment_type          AS INTEGER)   AS payment_type
FROM deduped
WHERE _rn = 1
