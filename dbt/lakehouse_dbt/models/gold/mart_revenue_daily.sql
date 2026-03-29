{{
    config(
        materialized  = 'external',
        location      = '../../data/gold/mart_revenue_daily.parquet',
        format        = 'parquet',
        options       = {'codec': 'snappy'}
    )
}}

SELECT
    DATE_TRUNC('day', pickup_datetime)::DATE AS trip_date,
    COUNT(*)                                 AS total_trips,
    ROUND(SUM(fare_amount),   2)             AS total_fare,
    ROUND(SUM(tip_amount),    2)             AS total_tips,
    ROUND(SUM(total_amount),  2)             AS total_revenue,
    ROUND(AVG(trip_distance), 4)             AS avg_distance_miles,
    ROUND(AVG(passenger_count), 2)           AS avg_passengers
FROM {{ ref('stg_trips') }}
GROUP BY 1
ORDER BY 1
