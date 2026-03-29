{{
    config(
        materialized = 'external',
        location     = '/opt/airflow/data/gold/mart_trips_by_location.parquet',
        format       = 'parquet',
        options      = {'codec': 'snappy'}
    )
}}

SELECT
    pickup_location_id,
    COUNT(*)                        AS total_trips,
    ROUND(SUM(total_amount),  2)    AS total_revenue,
    ROUND(AVG(fare_amount),   2)    AS avg_fare,
    ROUND(AVG(trip_distance), 4)    AS avg_distance_miles,
    ROUND(AVG(tip_amount),    2)    AS avg_tip,
    COUNT(DISTINCT DATE_TRUNC('day', pickup_datetime)::DATE) AS active_days
FROM {{ ref('stg_trips') }}
GROUP BY 1
ORDER BY total_trips DESC
