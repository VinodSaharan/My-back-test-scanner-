import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Only Sell Backtester", layout="wide")
st.title("📉 Only SHORT/SELL Intraday Strategy Backtester")
st.write("यह ऐप केवल मंदी (Short Selling) के सिग्नल्स को बैकटेस्ट करता है।")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Settings")
ticker = st.sidebar.text_input("Stock Ticker", value="TATAMOTORS.NS")

# Indicators Parameters (Optimized for Shorting)
st_length = st.sidebar.number_input("Supertrend Length (ATR)", min_value=5, value=10)
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, value=2.0, step=0.1)
rsi_period = st.sidebar.number_input("RSI Period", min_value=5, value=14)
ema_period = st.sidebar.number_input("EMA Period", min_value=10, value=50)

cash = st.sidebar.number_input("Starting Capital (INR)", value=100000)

# --- PURE PANDAS CALCULATIONS ---
def calculate_indicators(df, st_len=10, st_mult=2.0, rsi_len=14, ema_len=50):
    df = df.copy()
    
    # 1. EMA
    df['EMA'] = df['Close'].ewm(span=ema_len, adjust=False).mean()
    
    # 2. RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_len).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_len).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 3. Supertrend
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

# --- FETCH DATA (Error-Free 60 Days Combination) ---
try:
    # 60d period and 15m interval हमेशा काम करता है, चाहे वीकेंड हो या नहीं
    data = yf.download(tickers=ticker, period="60d", interval="15m")
    
    if data.empty:
        st.error("डेटा नहीं मिला! कृपया चेक करें कि स्टॉक का नाम सही है (उदा. SBIN.NS)")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success("पिछले 60 दिनों का 15-Min डेटा लोड हो गया है!")
        
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
            
            # EXIT SHORT: अगर पहले से शार्ट पोजीशन में हैं और Supertrend ग्रीन हो जाए या प्राइज EMA के ऊपर निकल जाए
            if in_short:
                if row['Direction'] == 1 or row['Close'] > row['EMA']:
                    pnl = ((entry_price - row['Close']) / entry_price) * 100  # शार्ट में गिरने पर प्रॉफिट
                    trades.append({'Trade Type': 'SHORT (Sell)', 'Entry Time': entry_time, 'Exit Time': index, 'Entry Price': entry_price, 'Exit Price': row['Close'], 'PnL%': pnl})
                    in_short = False
            
            # ENTRY SHORT: हाथ खाली है और Supertrend ग्रीन से रेड हुआ + प्राइज EMA के नीचे + RSI < 50
            else:
                if prev_row['Direction'] == 1 and row['Direction'] == -1:
                    if row['Close'] < row['EMA'] and row['RSI'] < 50:
                        in_short = True
                        entry_price = row['Close']
                        entry_time = index

        # --- DISPLAY RESULTS ---
        st.subheader("📊 Only Sell Performance Metrics")
        col1, col2 = st.columns(2)
        
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            
            total_trades = len(trades_df)
            win_trades = len(trades_df[trades_df['PnL%'] > 0])
            win_rate = (win_trades / total_trades) * 100
            total_return = trades_df['PnL%'].sum()
            final_equity = cash * (1 + (total_return/100))
            
            with col1:
                st.metric(label="Total Return from Shorting (%)", value=f"{total_return:.2f}%", delta=f"{total_return:.2f}%")
                st.metric(label="Final Capital", value=f"₹{final_equity:,.2f}")
                
            with col2:
                st.metric(label="Total Short Trades", value=total_trades)
                st.metric(label="Shorting Win Rate (%)", value=f"{win_rate:.2f}%")
                
            st.write("### 📝 Detailed Sell Trades Log")
            st.dataframe(trades_df[['Entry Time', 'Exit Time', 'Entry Price', 'Exit Price', 'PnL%']])
        else:
            st.warning("इस अवधि में इन कड़े नियमों पर कोई भी मंदी (Short) का ट्रेड नहीं मिला। कृपया मल्टिप्लायर या ईएमए थोड़ा कम करके देखें।")
            
        # Charts
        st.write("### 📉 Price vs Supertrend & EMA Chart")
        st.line_chart(df_result[['Close', 'Supertrend', 'EMA']])

except Exception as e:
    st.error(f"सिस्टम एरer: {e}")
