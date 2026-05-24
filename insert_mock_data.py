import os
import snowflake.connector

conn = snowflake.connector.connect(
    account=os.environ['SNOWFLAKE_ACCOUNT'],
    user=os.environ['SNOWFLAKE_USER'],
    password=os.environ['SNOWFLAKE_PASSWORD'],
    role='ALT_ENGINEER',
    database='ALT_DB'
)
cur = conn.cursor()
cur.execute("DELETE FROM ALT_DB.BRONZE.REALTIME_TRADE;")
cur.execute("""
INSERT INTO ALT_DB.BRONZE.REALTIME_TRADE (TRADE_ID, SYMBOL, PRICE, EMA, SPIKE_DETECTED, TRADE_TIMESTAMP)
SELECT 
  UUID_STRING(), 
  'BTC/USDT', 
  50000 + (UNIFORM(-1000, 1000, RANDOM())), 
  50000 + (UNIFORM(-500, 500, RANDOM())), 
  UNIFORM(0, 10, RANDOM()) >= 8, 
  DATEADD(SECOND, -SEQ4(), CURRENT_TIMESTAMP())
FROM TABLE(GENERATOR(ROWCOUNT => 100));
""")
print("Mock realtime trades inserted.")

cur.execute("DELETE FROM ALT_DB.BRONZE.RAW_TRADE;")
cur.execute("""
INSERT INTO ALT_DB.BRONZE.RAW_TRADE (PAYLOAD)
SELECT 
  OBJECT_CONSTRUCT(
      'id', UUID_STRING(),
      'symbol', 'BTC/USDT',
      'price', 50000 + (UNIFORM(-1000, 1000, RANDOM())),
      'amount', 1.5,
      'timestamp', DATE_PART(EPOCH_MILLISECOND, DATEADD(SECOND, -SEQ4() - 100, CURRENT_TIMESTAMP()))
  )
FROM TABLE(GENERATOR(ROWCOUNT => 100));
""")
print("Mock batch trades inserted.")
conn.close()
