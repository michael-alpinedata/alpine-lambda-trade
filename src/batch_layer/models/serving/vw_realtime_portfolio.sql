{{ config(materialized='view') }}

WITH historical AS (
    SELECT 
        h.trade_id,
        h.symbol,
        h.price,
        h.trade_timestamp,
        'BATCH' as source_layer,
        COALESCE(CAST(r.spike_detected AS BOOLEAN), FALSE) as spike_detected,
        CAST(r.ema AS FLOAT) as ema,
        CAST(r.upper_band AS FLOAT) as upper_band,
        CAST(r.lower_band AS FLOAT) as lower_band
    FROM {{ ref('slv_trades') }} h
    LEFT JOIN {{ source('alpine_lambda_trade_source', 'REALTIME_TRADE') }} r 
        ON h.trade_id = r.trade_id
),

real_time AS (
    SELECT 
        trade_id,
        symbol,
        price,
        trade_timestamp,
        'SPEED' as source_layer,
        -- Need to explicitly cast to BOOLEAN to prevent union conflicts or Variant parsing
        CAST(spike_detected AS BOOLEAN) as spike_detected,
        CAST(ema AS FLOAT) as ema,
        CAST(upper_band AS FLOAT) as upper_band,
        CAST(lower_band AS FLOAT) as lower_band
    FROM {{ source('alpine_lambda_trade_source', 'REALTIME_TRADE') }}
    -- Filter out overlaps seamlessly
    WHERE trade_timestamp > COALESCE((SELECT MAX(trade_timestamp) FROM historical), '1970-01-01'::TIMESTAMP)
)

SELECT * FROM historical
UNION ALL
SELECT * FROM real_time
