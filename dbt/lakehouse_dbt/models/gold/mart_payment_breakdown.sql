{{
    config(
        materialized = 'external',
        location     = '/opt/airflow/data/gold/mart_payment_breakdown.parquet',
        format       = 'parquet',
        options      = {'codec': 'snappy'}
    )
}}

SELECT
    payment_type,
    CASE payment_type
        WHEN 1 THEN 'Credit Card'
        WHEN 2 THEN 'Cash'
        WHEN 3 THEN 'No Charge'
        WHEN 4 THEN 'Dispute'
        WHEN 5 THEN 'Unknown'
        WHEN 6 THEN 'Voided Trip'
        ELSE 'Other'
    END                                                          AS payment_method,
    COUNT(*)                                                     AS total_trips,
    ROUND(SUM(total_amount), 2)                                  AS total_revenue,
    ROUND(AVG(fare_amount),  2)                                  AS avg_fare,
    ROUND(AVG(tip_amount),   2)                                  AS avg_tip,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)          AS pct_of_trips,
    ROUND(100.0 * SUM(total_amount) / SUM(SUM(total_amount)) OVER (), 2) AS pct_of_revenue
FROM {{ ref('stg_trips') }}
GROUP BY 1, 2
ORDER BY total_trips DESC
