{{ config(
    materialized='incremental',
    unique_key='trade_id'
) }}

WITH staged AS (
    SELECT * FROM {{ ref('stg_trades') }}

{% if is_incremental() %}
    -- Process only new records (comparing on the internal timestamp)
    WHERE trade_timestamp > coalesce((SELECT max(trade_timestamp) FROM {{ this }}), '1970-01-01'::TIMESTAMP)
{% endif %}
),

deduplicated AS (
    SELECT 
        *,
        ROW_NUMBER() OVER(PARTITION BY trade_id ORDER BY trade_timestamp DESC) as rn
    FROM staged
)

SELECT
    trade_id,
    symbol,
    price,
    amount,
    cost,
    side,
    trade_timestamp,
    trade_datetime_str,
    -- Audit Metadata
    CURRENT_TIMESTAMP() AS loaded_at
FROM deduplicated
WHERE rn = 1
