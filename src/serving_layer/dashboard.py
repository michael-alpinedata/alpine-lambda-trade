import streamlit as st
import snowflake.connector
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="ALT Real-Time Portfolio", layout="wide")

@st.cache_resource
def init_connection():
    return snowflake.connector.connect(
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        database="ALT_DB",
        schema="STAGING" 
    )

sf = init_connection()

st.title("🚀 Alpine Lambda Trade (ALT) - Real-Time Portfolio")

@st.cache_data(ttl=5) # Real-Time caching every 5 seconds
def get_historical_data():
    cursor = sf.cursor()
    cursor.execute("""
    SELECT 
        TRADE_TIMESTAMP,
        SYMBOL,
        PRICE,
        SOURCE_LAYER,
        SPIKE_DETECTED,
        EMA,
        UPPER_BAND,
        LOWER_BAND
    FROM ALT_DB.STAGING_SERVING.VW_REALTIME_PORTFOLIO
    ORDER BY TRADE_TIMESTAMP DESC
    LIMIT 2000
    """)
    # Fetch using fetchall() to avoid PyArrow LargeUtf8 typing issues in Streamlit
    results = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    df = pd.DataFrame(results, columns=columns)
    
    return df
@st.cache_data(ttl=5)
def get_kpis():
    cursor = sf.cursor()
    query = """
    SELECT 
        COUNT(*) as TOTAL_TRADES,
        SUM(IFF(SPIKE_DETECTED = TRUE AND TRADE_TIMESTAMP >= DATEADD(HOUR, -1, CURRENT_TIMESTAMP()), 1, 0)) as RECENT_SPIKES
    FROM ALT_DB.STAGING_SERVING.VW_REALTIME_PORTFOLIO
    """
    cursor.execute(query)
    return cursor.fetch_pandas_all()

df = get_historical_data()
kpis_df = get_kpis()

# Header KPIs
total_trades = kpis_df['TOTAL_TRADES'].iloc[0] if not kpis_df.empty else 0
recent_spikes = kpis_df['RECENT_SPIKES'].iloc[0] if not kpis_df.empty else 0
# Gracefully handle NaN or None when counting spikes
recent_spikes = int(recent_spikes) if pd.notna(recent_spikes) else 0

if not df.empty:
    symbols = df['SYMBOL'].unique()
    num_cols = 2 + len(symbols)
    cols = st.columns(num_cols)
    
    cols[0].metric("📈 Total Trades", f"{total_trades:,}")
    cols[1].metric("⚠️ Spikes (1H)", recent_spikes)
    
    for i, symbol in enumerate(symbols):
        latest_sym = df[df['SYMBOL'] == symbol].iloc[0]
        curr_price = latest_sym['PRICE']
        curr_ema = latest_sym['EMA'] if pd.notna(latest_sym['EMA']) else curr_price
        diff = curr_price - curr_ema
        cols[2 + i].metric(f"🎯 {symbol} vs EMA", f"${curr_price:,.2f}", f"{diff:,.2f} Delta" if diff != 0 else "0.00")
else:
    cols = st.columns(2)
    cols[0].metric("📈 Total Trades", f"{total_trades:,}")
    cols[1].metric("⚠️ Spikes (1H)", recent_spikes)
st.divider()

st.subheader("Price Movements & Volatility Anomalies")

if not df.empty:
    min_time = df['TRADE_TIMESTAMP'].min()
    max_time = df['TRADE_TIMESTAMP'].max()
    time_domain = [min_time, max_time]

    symbols = df['SYMBOL'].unique()
    
    for symbol in symbols:
        symbol_df = df[df['SYMBOL'] == symbol]
        
        # 1. Base du graphique
        base = alt.Chart(symbol_df).properties(
            height=280,
            width='container',
            title=f"Market Trend: {symbol}"
        ).encode(
            x=alt.X('TRADE_TIMESTAMP:T', 
                    title='Time', 
                    axis=alt.Axis(format='%H:%M:%S'),
                    scale=alt.Scale(domain=time_domain))
        )

        # 1. Bollinger Band Zone (Shaded Area)
        bollinger_band = base.mark_area(opacity=0.1, color='gray').encode(
            y=alt.Y('UPPER_BAND:Q'),
            y2=alt.Y2('LOWER_BAND:Q')
        )

        # 2. Price Curve (Blue)
        price_line = base.transform_calculate(
            Type='datum.SYMBOL + " Price"'
        ).mark_line(color='#1f77b4').encode(
            y=alt.Y('PRICE:Q', scale=alt.Scale(zero=False), title='Price ($)'),
            color=alt.Color('Type:N', scale=alt.Scale(range=['#1f77b4']), legend=alt.Legend(title=None))
        )
        
        # 3. EMA Curve (Orange dashed)
        ema_line = base.transform_calculate(
            Type='datum.SYMBOL + " EMA (Speed Layer)"'
        ).mark_line(strokeDash=[5, 5], color='#ff7f0e').encode(
            y=alt.Y('EMA:Q'),
            color=alt.Color('Type:N', scale=alt.Scale(range=['#ff7f0e']), legend=alt.Legend(title=None))
        )

        # 4. Anomaly Points (Spikes)
        spikes = base.transform_filter(
            alt.datum.SPIKE_DETECTED == True
        ).mark_point(color='red', size=160, shape='diamond').encode(
            y='PRICE:Q',
            tooltip=['PRICE', 'EMA', 'UPPER_BAND', 'LOWER_BAND', 'SOURCE_LAYER']
        )

        # 5. Layer everything
        combined = alt.layer(bollinger_band, ema_line, price_line, spikes).resolve_scale(color='independent')
        
        st.altair_chart(combined, use_container_width=True)

st.subheader("Last 50 Ledger Transactions")
# Style dataframe to highlight the source
if not df.empty:
    st.dataframe(df.head(50), use_container_width=True)

# Auto-refresh du dashboard toutes les 5 secondes
import time
time.sleep(5)
st.rerun()
