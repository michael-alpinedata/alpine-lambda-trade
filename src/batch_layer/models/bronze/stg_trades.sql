{{ config(materialized='view') }}

WITH raw AS (
    SELECT 
        PAYLOAD
    FROM {{ source('alpine_lambda_trade_source', 'RAW_TRADE') }}
)

SELECT
    PAYLOAD:id::STRING AS trade_id,
    PAYLOAD:symbol::STRING AS symbol,
    PAYLOAD:price::FLOAT AS price,
    PAYLOAD:amount::FLOAT AS amount,
    PAYLOAD:cost::FLOAT AS cost,
    PAYLOAD:side::STRING AS side,
    -- CCXT timestamps are in milliseconds
    TO_TIMESTAMP_NTZ(PAYLOAD:timestamp::NUMBER, 3) AS trade_timestamp,
    PAYLOAD:datetime::STRING AS trade_datetime_str
FROM raw
