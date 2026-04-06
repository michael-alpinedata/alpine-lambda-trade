import os
import snowflake.connector
import pandas as pd
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(".env")

def check_data():
    try:
        conn = snowflake.connector.connect(
            user=os.environ['SNOWFLAKE_USER'],
            password=os.environ['SNOWFLAKE_PASSWORD'],
            account=os.environ['SNOWFLAKE_ACCOUNT'],
            database='ALT_DB',
            schema='STAGING'
        )
        
        cursor = conn.cursor()
        print("Querying STG_REALTIME...")
        cursor.execute("SELECT * FROM STG_REALTIME ORDER BY TRADE_TIMESTAMP DESC LIMIT 5")
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()
        df = pd.DataFrame(results, columns=columns)
        print(df)
        conn.close()
    except Exception as e:
        print(f"Error checking data: {e}")

if __name__ == "__main__":
    check_data()
