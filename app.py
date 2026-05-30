import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Ultimate Algo Backtester", layout="wide")
st.title("🏆 Ultimate All-Weather Intraday Strategy (3-Month Data)")
st.write("मार्केट की दिशा के साथ चलने वाली सबसे सफल और प्रैक्टिकल ट्रेडिंग रणनीति")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Settings")
ticker = st.sidebar.text_input("Stock Ticker", value="SBIN.NS")

# Professional Golden Combo Parameters
fast_ema = st.sidebar.number_input("Fast EMA (एंट्री स्पीड)", min_value=5, value=9)
slow_ema = st.sidebar.number_input("Slow EMA (ट्रेंड फिल्टर)", min_value=10, value=21)
st_length = st.sidebar.number_input("Supertrend Length", min_value=5, value=10)
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, value=2.5, step=0.1)

cash = st.sidebar.number_input("Starting Capital (INR)", value=100000)

# --- ADVANCED 3-MONTH DATA FETCHING ---
def fetch_3_month_intraday(symbol):
    today = datetime.now()
    start_date = today - timedelta(days=90)
    mid_date = today - timedelta(days=45)
    
    df1 = yf.download(tickers=symbol, start=start_date.strftime('%Y-%m-%d'), end=mid_date.strftime('%Y-%m-%d'), interval="15m", progress=False)
    df2 = yf.download(tickers=symbol, start=mid_date.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'), interval="15m", progress=False)
    
    combined_df = pd.concat([df1, df2])
    combined_df = combined_df.loc[~combined_df.index.duplicated(keep='first')].sort_index()
    return combined_df

# --- INDICATORS ENGINE ---
def calculate_indicators(df, f_ema=9, s_ema=21, st_len=10, st_mult=2.5):
    df = df.copy()
    
    # EMAs for Trend Check
    df['EMA_Fast'] = df['Close'].ewm(span=f_ema, adjust=False).mean()
    df['EMA_Slow'] = df['Close'].ewm(span=s_ema, adjust=False).mean()
    
    # Supertrend
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

# --- EXPERT TRADING SYSTEM ---
try:
    data = fetch_3_month_intraday(ticker)
    
    if data.empty:
        st.error("डेटा लिंक में समस्या है!")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success("पिछले 3 महीने का डेटा सफलतापूर्वक प्रोसेस हो गया है!")
        df_result = calculate_indicators(data, fast_ema, slow_ema, st_length, st_multiplier)
        
        trades = []
        position = None # "LONG", "SHORT", or None
        entry_price = 0
        entry_time = None
        
        for i in range(1, len(df_result)):
            row = df_result.iloc[i]
            prev_row = df_result.iloc[i-1]
            index = df_result.index[i]
            
            # 1. POSITION EXIT LOGIC
            if position == "LONG":
                if row['Direction'] == -1 or row['EMA_Fast'] < row['EMA_Slow']:
                    pnl = ((row['Close'] - entry_price) / entry_price) * 100
                    trades.append({'Type': 'BUY (Long)', 'Entry': entry_time, 'Exit': index, 'PnL%': pnl})
                    position = None
            elif position == "SHORT":
                if row['Direction'] == 1 or row['EMA_Fast'] > row['EMA_Slow']:
                    pnl = ((entry_price - row['Close']) / entry_price) * 100
                    trades.append({'Type': 'SHORT (Sell)', 'Entry': entry_time, 'Exit': index, 'PnL%': pnl})
                    position = None
                    
            # 2. POSITION ENTRY LOGIC
            if position is None:
                # BUY: Supertrend turned green AND 9 EMA is above 21 EMA (Bullish Market)
                if prev_row['Direction'] == -1 and row['Direction'] == 1 and row['EMA_Fast'] > row['EMA_Slow']:
                    position = "LONG"
                    entry_price = row['Close']
                    entry_time = index
                # SHORT: Supertrend turned red AND 9 EMA is below 21 EMA (Bearish Market)
                elif prev_row['Direction'] == 1 and row['Direction'] == -1 and row['EMA_Fast'] < row['EMA_Slow']:
                    position = "SHORT"
                    entry_price = row['Close']
                    entry_time = index

        # --- DISPLAY REPORT ---
        st.subheader("📊 Master Strategy Performance Report")
        col1, col2 = st.columns(2)
        
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_trades = len(trades_df)
            win_trades = len(trades_df[trades_df['PnL%'] > 0])
            win_rate = (win_trades / total_trades) * 100
            total_return = trades_df['PnL%'].sum()
            final_equity = cash * (1 + (total_return/100))
            
            with col1:
                st.metric(label="Total Return (%) 💰", value=f"{total_return:.2f}%", delta=f"{total_return:.2f}%")
                st.metric(label="Final Value (₹)", value=f"₹{final_equity:,.2f}")
            with col2:
                st.metric(label="Total Trades", value=total_trades)
                st.metric(label="Win Rate (%)", value=f"{win_rate:.2f}%")
                
            st.write("### 📝 Detailed Trade Book")
            st.dataframe(trades_df)
        else:
            st.warning("इस स्टॉक में अभी कोई मजबूत ट्रेंड नहीं है। कृपया दूसरा टिकर ट्राई करें।")
            
        # Chart
        st.write("### 📉 Multi-Trend Analysis Chart")
        st.line_chart(df_result[['Close', 'EMA_Fast', 'EMA_Slow']])

except Exception as e:
    st.error(f"एरर: {e}")
