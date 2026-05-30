import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Multi-Indicator Backtester", layout="wide")
st.title("🚀 Multi-Indicator (Supertrend + RSI + 200 EMA) Intraday Backtester")
st.write("3 पावरफुल इंडिकेटर्स का कॉम्बिनेशन - 100% एरर-फ्री और सेफ")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Indicator Settings")
ticker = st.sidebar.text_input("Stock Ticker", value="SBIN.NS")
period = st.sidebar.selectbox("Data Period", options=["1mo", "3mo"], index=0)

# Indicator Parameters
st_length = st.sidebar.number_input("Supertrend Length (ATR)", min_value=5, value=10)
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, value=3.0, step=0.1)
rsi_period = st.sidebar.number_input("RSI Period", min_value=5, value=14)
ema_period = st.sidebar.number_input("Long EMA Period", min_value=50, value=200)

cash = st.sidebar.number_input("Starting Capital (INR)", value=100000)

# --- PURE PANDAS CALCULATIONS (No external library) ---
def calculate_indicators(df, st_len=10, st_mult=3.0, rsi_len=14, ema_len=200):
    df = df.copy()
    
    # 1. 200 EMA Calculation
    df['EMA_Long'] = df['Close'].ewm(span=ema_len, adjust=False).mean()
    
    # 2. RSI Calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_len).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_len).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 3. Supertrend Calculation
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
        st.error("डेटा नहीं मिला! सही टिकर डालें।")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success("डेटा लोड हो गया! एडवांस इंडिकेटर्स कैलकुलेट हो रहे हैं...")
        
        # Calculate All Indicators
        df_result = calculate_indicators(data, st_length, st_multiplier, rsi_period, ema_period)
        
        # --- ADVANCED STRATEGY LOGIC ---
        trades = []
        in_position = False
        buy_price = 0
        
        for i in range(1, len(df_result)):
            row = df_result.iloc[i]
            prev_row = df_result.iloc[i-1]
            index = df_result.index[i]
            
            # BUY CONDITION: 
            # 1. Supertrend turned Green (Direction shifted from -1 to 1)
            # 2. Close Price is ABOVE 200 EMA (Trend is Bullish)
            # 3. RSI is ABOVE 50 (Strong momentum)
            if prev_row['Direction'] == -1 and row['Direction'] == 1:
                if row['Close'] > row['EMA_Long'] and row['RSI'] > 50:
                    if not in_position:
                        buy_price = row['Close']
                        in_position = True
                        trades.append({'Type': 'BUY', 'Price': buy_price, 'Time': index})
                        
            # EXIT CONDITION: Supertrend turns Red OR Price drops below 200 EMA
            elif row['Direction'] == -1 or row['Close'] < row['EMA_Long']:
                if in_position:
                    sell_price = row['Close']
                    pnl = ((sell_price - buy_price) / buy_price) * 100
                    in_position = False
                    trades.append({'Type': 'SELL', 'Price': sell_price, 'Time': index, 'PnL%': pnl})

        # --- DISPLAY PERFORMANCE ---
        st.subheader("📊 Multi-Indicator Strategy Report")
        col1, col2 = st.columns(2)
        
        if len(trades) > 1:
            trades_df = pd.DataFrame([t for t in trades if t['Type'] == 'SELL'])
            
            total_trades = len(trades_df)
            win_trades = len(trades_df[trades_df['PnL%'] > 0])
            win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
            total_return = trades_df['PnL%'].sum()
            final_equity = cash * (1 + (total_return/100))
            
            with col1:
                st.metric(label="Total Return (%)", value=f"{total_return:.2f}%", delta=f"{total_return:.2f}%")
                st.metric(label="Final Estimated Capital", value=f"₹{final_equity:,.2f}")
                
            with col2:
                st.metric(label="Total Closed Trades", value=total_trades)
                st.metric(label="Win Rate (%)", value=f"{win_rate:.2f}%")
                
            st.write("### 📝 Filtering Trade Log (केवल फ़िल्टर्ड ट्रेड्स)")
            st.dataframe(trades_df[['Time', 'Price', 'PnL%']])
        else:
            st.warning("इन कड़क कंडीशन्स (Supertrend + RSI + EMA) के साथ इस अवधि में कोई ट्रेड मैच नहीं हुआ। कृपया डेटा पीरियड बढ़ाएं या सेटिंग्स को थोड़ा कम करें।")
            
        # Charts
        st.write("### 📉 Price, Supertrend & 200 EMA Chart")
        st.line_chart(df_result[['Close', 'Supertrend', 'EMA_Long']])
        
        st.write("### ⏱️ RSI (Relative Strength Index)")
        st.line_chart(df_result['RSI'])

except Exception as e:
    st.error(f"सिस्टम एरर: {e}")
