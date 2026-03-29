{{
    config(
        materialized = 'external',
        location     = '../../data/gold/mart_trips_by_hour.parquet',
        format       = 'parquet',
        options      = {'codec': 'snappy'}
    )
}}

SELECT
    EXTRACT(hour FROM pickup_datetime)::INTEGER AS hour_of_day,
    COUNT(*)                                    AS total_trips,
    ROUND(SUM(total_amount),  2)                AS total_revenue,
    ROUND(AVG(fare_amount),   2)                AS avg_fare,
    ROUND(AVG(tip_amount),    2)                AS avg_tip,
    ROUND(AVG(trip_distance), 4)                AS avg_distance_miles,
    ROUND(AVG(passenger_count), 2)              AS avg_passengers
FROM {{ ref('stg_trips') }}
GROUP BY 1
ORDER BY 1
