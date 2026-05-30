import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="3-Month Only Sell Backtester", layout="wide")
st.title("📉 3-Month Only SHORT/SELL Intraday Backtester")
st.write("15-Min टाइमफ्रेम पर पिछले पूरे 3 महीने का डेटा (बिना किसी Yahoo Finance एरर के)")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Settings")
ticker = st.sidebar.text_input("Stock Ticker", value="TATAMOTORS.NS")

# Indicators Parameters
st_length = st.sidebar.number_input("Supertrend Length (ATR)", min_value=5, value=10)
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, value=2.0, step=0.1)
rsi_period = st.sidebar.number_input("RSI Period", min_value=5, value=14)
ema_period = st.sidebar.number_input("EMA Period", min_value=10, value=50)

cash = st.sidebar.number_input("Starting Capital (INR)", value=100000)

# --- ADVANCED 3-MONTH DATA FETCHING FUNCTION ---
def fetch_3_month_intraday(symbol):
    # आज से पिछले 90 दिनों (3 महीने) का डेटा टुकड़ों में निकालना
    today = datetime.now()
    start_date = today - timedelta(days=90)
    mid_date = today - timedelta(days=45)
    
    # Chunk 1: पहले 45 दिन
    st.write("⏳ डेटा का पहला हिस्सा लोड हो रहा है...")
    df1 = yf.download(tickers=symbol, start=start_date.strftime('%Y-%m-%d'), end=mid_date.strftime('%Y-%m-%d'), interval="15m", progress=False)
    
    # Chunk 2: आखिरी 45 दिन
    st.write("⏳ डेटा का दूसरा हिस्सा लोड हो रहा है...")
    df2 = yf.download(tickers=symbol, start=mid_date.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'), interval="15m", progress=False)
    
    # दोनों को आपस में जोड़ना (Concatenate)
    combined_df = pd.concat([df1, df2])
    # डुप्लीकेट्स हटाना और समय के अनुसार सेट करना
    combined_df = combined_df.loc[~combined_df.index.duplicated(keep='first')].sort_index()
    return combined_df

# --- PURE PANDAS INDICATORS ---
def calculate_indicators(df, st_len=10, st_mult=2.0, rsi_len=14, ema_len=50):
    df = df.copy()
    df['EMA'] = df['Close'].ewm(span=ema_len, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_len).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_len).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = (df['High'] - df['Close'].shift(1)).abs()
    df['L-PC'] = (df['Low'] - df['Close'].shift(1)).abs()
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=st_len).mean()
    
    hl2 = (df['High'] + df['Low']) / 2
    df['Basic_UB'] = hl2 + (st_mult * df['ATR'])
    df['Basic_LB'] = hl2 - (st_mult * df['ATR'])
    df['Final_UB'] = df['Basic_UB']
    df['Final_LB'] = df['Basic_LB']
    df['Supertrend'] = 0.0
    df['Direction'] = 1
    
    for i in range(1, len(df)):
        if df['Basic_UB'].iloc[i] < df['Final_UB'].iloc[i-1] or df['Close'].iloc[i-1] > df['Final_UB'].iloc[i-1]:
            df.loc[df.index[i], 'Final_UB'] = df['Basic_UB'].iloc[i]
        else:
            df.loc[df.index[i], 'Final_UB'] = df['Final_UB'].iloc[i-1]
            
        if df['Basic_LB'].iloc[i] > df['Final_LB'].iloc[i-1] or df['Close'].iloc[i-1] < df['Final_LB'].iloc[i-1]:
            df.loc[df.index[i], 'Final_LB'] = df['Basic_LB'].iloc[i]
        else:
            df.loc[df.index[i], 'Final_LB'] = df['Final_LB'].iloc[i-1]
            
        if df['Direction'].iloc[i-1] == 1:
            df.loc[df.index[i], 'Direction'] = 1 if df['Close'].iloc[i] > df['Final_LB'].iloc[i] else -1
        else:
            df.loc[df.index[i], 'Direction'] = -1 if df['Close'].iloc[i] < df['Final_UB'].iloc[i] else 1
            
        df.loc[df.index[i], 'Supertrend'] = df['Final_LB'].iloc[i] if df['Direction'].iloc[i] == 1 else df['Final_UB'].iloc[i]
        
    return df

# --- RUN SYSTEM ---
try:
    data = fetch_3_month_intraday(ticker)
    
    if data.empty:
        st.error("डेटा नहीं मिला! सही टिकर डालें (उदा. SBIN.NS)")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success(f"मज़ेदार खबर! पिछले 3 महीने की कुल {data.shape[0]} कैंडल्स सफलतापूर्वक कंबाइन हो गई हैं।")
        
        df_result = calculate_indicators(data, st_length, st_multiplier, rsi_period, ema_period)
        
        # --- ONLY SHORT/SELL TRADING LOGIC ---
        trades = []
        in_short = False
        entry_price = 0
        entry_time = None
        
        for i in range(1, len(df_result)):
            row = df_result.iloc[i]
            prev_row = df_result.iloc[i-1]
            index = df_result.index[i]
            
            if in_short:
                if row['Direction'] == 1 or row['Close'] > row['EMA']:
                    pnl = ((entry_price - row['Close']) / entry_price) * 100
                    trades.append({'Trade Type': 'SHORT (Sell)', 'Entry Time': entry_time, 'Exit Time': index, 'Entry Price': entry_price, 'Exit Price': row['Close'], 'PnL%': pnl})
                    in_short = False
            else:
                if prev_row['Direction'] == 1 and row['Direction'] == -1:
                    if row['Close'] < row['EMA'] and row['RSI'] < 50:
                        in_short = True
                        entry_price = row['Close']
                        entry_time = index

        # --- DISPLAY RESULTS ---
        st.subheader("📊 3-Month Only Sell Report")
        col1, col2 = st.columns(2)
        
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            
            total_trades = len(trades_df)
            win_trades = len(trades_df[trades_df['PnL%'] > 0])
            win_rate = (win_trades / total_trades) * 100
            total_return = trades_df['PnL%'].sum()
            final_equity = cash * (1 + (total_return/100))
            
            with col1:
                st.metric(label="Total Return (3 Months) (%)", value=f"{total_return:.2f}%", delta=f"{total_return:.2f}%")
                st.metric(label="Final Capital", value=f"₹{final_equity:,.2f}")
                
            with col2:
                st.metric(label="Total Short Trades", value=total_trades)
                st.metric(label="Shorting Win Rate (%)", value=f"{win_rate:.2f}%")
                
            st.write("### 📝 Detailed 3-Month Sell Trades Log")
            st.dataframe(trades_df[['Entry Time', 'Exit Time', 'Entry Price', 'Exit Price', 'PnL%']])
        else:
            st.warning("इस लंबे 3 महीने के इतिहास में इस कड़े नियम पर कोई ट्रेड नहीं मिला। साइडबार से सेटिंग्स बदलें।")
            
        # Charts
        st.write("### 📉 3-Month Price vs Supertrend Chart")
        st.line_chart(df_result[['Close', 'Supertrend']])

except Exception as e:
    st.error(f"सिस्टम एरर: {e}")
