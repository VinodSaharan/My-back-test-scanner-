import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Bi-Directional Backtester", layout="wide")
st.title("🏹 Both-Side (BUY & SHORT) Intraday Backtester")
st.write("मार्केट ऊपर जाए या नीचे, दोनों तरफ से प्रॉफिट कमाने वाली एडवांस रणनीति")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Indicator Settings")
ticker = st.sidebar.text_input("Stock Ticker", value="TATAMOTORS.NS") # डिफ़ॉल्ट हाई-मोमेंटम स्टॉक
period = st.sidebar.selectbox("Data Period", options=["1mo", "3mo"], index=0)

# Optimized Settings for 15-Min
st_length = st.sidebar.number_input("Supertrend Length (ATR)", min_value=5, value=10)
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, value=2.0, step=0.1) # 2.0 किया फॉर फास्ट एंट्री
rsi_period = st.sidebar.number_input("RSI Period", min_value=5, value=14)
ema_period = st.sidebar.number_input("Long EMA Period", min_value=20, value=50) # 50 किया ताकि ट्रेंड जल्दी पकड़े

cash = st.sidebar.number_input("Starting Capital (INR)", value=100000)

# --- PURE PANDAS CALCULATIONS ---
def calculate_indicators(df, st_len=10, st_mult=2.0, rsi_len=14, ema_len=50):
    df = df.copy()
    
    # 1. EMA
    df['EMA_Long'] = df['Close'].ewm(span=ema_len, adjust=False).mean()
    
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

# --- FETCH & PROCESS ---
try:
    data = yf.download(tickers=ticker, period=period, interval="15m")
    
    if data.empty:
        st.error("डेटा नहीं मिला!")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success("डेटा लोड हो गया! दोनों तरफ के सिग्नल्स प्रोसेस हो रहे हैं...")
        
        df_result = calculate_indicators(data, st_length, st_multiplier, rsi_period, ema_period)
        
        # --- ADVANCED DOUBLE-SIDED TRADING LOGIC ---
        trades = []
        position_type = None # "BUY", "SHORT", or None
        entry_price = 0
        entry_time = None
        
        for i in range(1, len(df_result)):
            row = df_result.iloc[i]
            prev_row = df_result.iloc[i-1]
            index = df_result.index[i]
            
            # --- 1. EXIT CONDITIONS ---
            if position_type == "BUY":
                # Exit Long if Supertrend turns Red OR Price goes below EMA
                if row['Direction'] == -1 or row['Close'] < row['EMA_Long']:
                    pnl = ((row['Close'] - entry_price) / entry_price) * 100
                    trades.append({'Trade Type': 'BUY (Long)', 'Entry Time': entry_time, 'Exit Time': index, 'Entry Price': entry_price, 'Exit Price': row['Close'], 'PnL%': pnl})
                    position_type = None
                    
            elif position_type == "SHORT":
                # Exit Short if Supertrend turns Green OR Price goes above EMA
                if row['Direction'] == 1 or row['Close'] > row['EMA_Long']:
                    pnl = ((entry_price - row['Close']) / entry_price) * 100 # Short में गिरने पर फायदा होता है
                    trades.append({'Trade Type': 'SHORT (Sell)', 'Entry Time': entry_time, 'Exit Time': index, 'Entry Price': entry_price, 'Exit Price': row['Close'], 'PnL%': pnl})
                    position_type = None

            # --- 2. ENTRY CONDITIONS (जब हाथ खाली हो) ---
            if position_type is None:
                # BUY Entry
                if prev_row['Direction'] == -1 and row['Direction'] == 1:
                    if row['Close'] > row['EMA_Long'] and row['RSI'] > 50:
                        position_type = "BUY"
                        entry_price = row['Close']
                        entry_time = index
                        
                # SHORT Entry
                elif prev_row['Direction'] == 1 and row['Direction'] == -1:
                    if row['Close'] < row['EMA_Long'] and row['RSI'] < 50:
                        position_type = "SHORT"
                        entry_price = row['Close']
                        entry_time = index

        # --- DISPLAY RESULTS ---
        st.subheader("📊 Both-Side Performance Report")
        col1, col2 = st.columns(2)
        
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            
            total_trades = len(trades_df)
            win_trades = len(trades_df[trades_df['PnL%'] > 0])
            win_rate = (win_trades / total_trades) * 100
            total_return = trades_df['PnL%'].sum()
            final_equity = cash * (1 + (total_return/100))
            
            with col1:
                st.metric(label="Total Combined Return (%)", value=f"{total_return:.2f}%", delta=f"{total_return:.2f}%")
                st.metric(label="Final Capital", value=f"₹{final_equity:,.2f}")
                
            with col2:
                st.metric(label="Total Executed Trades", value=total_trades)
                st.metric(label="Strategy Win Rate (%)", value=f"{win_rate:.2f}%")
                
            # Full Log Table
            st.write("### 📝 Master Trade Log (Buy & Short दोनों की लिस्ट)")
            st.dataframe(trades_df[['Trade Type', 'Entry Time', 'Exit Time', 'Entry Price', 'Exit Price', 'PnL%']])
        else:
            st.warning("इस अवधि में इन पैमानों पर कोई ट्रेड नहीं बना।")
            
        # Charts
        st.write("### 📉 Multi-Indicator Price Chart")
        st.line_chart(df_result[['Close', 'Supertrend', 'EMA_Long']])

except Exception as e:
    st.error(f"सिस्टम एरर: {e}")
