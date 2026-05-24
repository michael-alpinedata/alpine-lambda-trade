import os
import json
import base64
import logging
import numpy as np
from collections import deque
import logging
import snowflake.connector

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Module-level cache for Warm invocations across batches
# Memory layout: { 'BTC/USDT': { 'ema': 50000.0, 'prices': deque([...]), 'alpha': 0.1 } }
ema_cache = {}
THRESHOLD = 0.02 # 2% anomaly spike variation allowed

sf_conn = None

def get_snowflake_connection():
    return snowflake.connector.connect(
        user=os.environ['SNOWFLAKE_USER'],
        password=os.environ['SNOWFLAKE_PASSWORD'],
        account=os.environ['SNOWFLAKE_ACCOUNT'],
        database='ALT_DB',
        schema='BRONZE'
    )

def lambda_handler(event, context):
    global sf_conn
    
    if sf_conn is None or sf_conn.is_closed():
        logger.info("Initializing fresh Snowflake connection")
        sf_conn = get_snowflake_connection()

    records_to_insert = []
    
    for record in event['Records']:
        payload = record['body']
        try:
            trade = json.loads(payload)
        except Exception as e:
            logger.error(f"Failed parsing json Payload: {e}")
            continue
            
        symbol = trade.get('symbol')
        price = float(trade.get('price', 0))
        trade_id = trade.get('id')
        dt = trade.get('datetime')
        
        # EMA & Bollinger Core Mathematical Logic
        if symbol not in ema_cache:
            ema_cache[symbol] = { 
                'ema': price, 
                'prices': deque([price], maxlen=20),
                'alpha': 0.02 
            }
        else:
            prev_ema = ema_cache[symbol]['ema']
            alpha = ema_cache[symbol]['alpha']
            # EMA Update
            new_ema = (price * alpha) + (prev_ema * (1 - alpha))
            ema_cache[symbol]['ema'] = new_ema
            # Rolling Window for Bollinger
            ema_cache[symbol]['prices'].append(price)
        
        current_ema = ema_cache[symbol]['ema']
        
        # Bollinger Bands Calculation
        prices_window = list(ema_cache[symbol]['prices'])
        std_dev = float(np.std(prices_window)) if len(prices_window) > 1 else 0.0
        upper_band = float(current_ema + (2 * std_dev))
        lower_band = float(current_ema - (2 * std_dev))
        
        spike_detected = bool(abs(price - current_ema) / current_ema > THRESHOLD)

        records_to_insert.append((
            trade_id, symbol, float(price), float(current_ema), upper_band, lower_band, spike_detected, dt
        ))
        
    if records_to_insert:
        try:
            cursor = sf_conn.cursor()
            query = """
            INSERT INTO REALTIME_TRADE (TRADE_ID, SYMBOL, PRICE, EMA, UPPER_BAND, LOWER_BAND, SPIKE_DETECTED, TRADE_TIMESTAMP)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(query, records_to_insert)
            logger.info(f"Inserted {len(records_to_insert)} records into REALTIME_TRADE successfully.")
        except Exception as e:
            logger.error(f"Snowflake Insert Error: {e}")
            raise e

    return {
        'statusCode': 200,
        'body': f"Speed Layer logic processed {len(records_to_insert)} trades"
    }
