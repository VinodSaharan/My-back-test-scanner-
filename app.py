import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Safe Intraday Backtester", layout="wide")
st.title("🚀 Custom 15-Min Supertrend Backtester")
st.write("बिना किसी बाहरी लाइब्रेरी एरर के 100% सुरक्षित और फास्ट बैकटेस्टर")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Settings")
ticker = st.sidebar.text_input("Stock Ticker", value="SBIN.NS")
period = st.sidebar.selectbox("Data Period", options=["1mo", "3mo"], index=0)

# Supertrend Engine (Built-in Pandas)
st_length = st.sidebar.number_input("Supertrend Length (ATR)", min_value=5, value=10)
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, value=3.0, step=0.1)

cash = st.sidebar.number_input("Starting Capital (INR)", value=100000)

# --- PURE PANDAS SUPERTREND FUNCTION ---
def calculate_supertrend(df, period=10, multiplier=3):
    df = df.copy()
    # True Range (TR) Calculation
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = (df['High'] - df['Close'].shift(1)).abs()
    df['L-PC'] = (df['Low'] - df['Close'].shift(1)).abs()
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    
    # Average True Range (ATR)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    
    # Basic Upper & Lower Bands
    hl2 = (df['High'] + df['Low']) / 2
    df['Basic_UB'] = hl2 + (multiplier * df['ATR'])
    df['Basic_LB'] = hl2 - (multiplier * df['ATR'])
    
    # Final Bands & Trend Direction
    df['Final_UB'] = df['Basic_UB']
    df['Final_LB'] = df['Basic_LB']
    df['Supertrend'] = 0.0
    df['Direction'] = 1  # 1 for Buy, -1 for Sell
    
    for i in range(1, len(df)):
        # Upper Band Logic
        if df['Basic_UB'].iloc[i] < df['Final_UB'].iloc[i-1] or df['Close'].iloc[i-1] > df['Final_UB'].iloc[i-1]:
            df.loc[df.index[i], 'Final_UB'] = df['Basic_UB'].iloc[i]
        else:
            df.loc[df.index[i], 'Final_UB'] = df['Final_UB'].iloc[i-1]
            
        # Lower Band Logic
        if df['Basic_LB'].iloc[i] > df['Final_LB'].iloc[i-1] or df['Close'].iloc[i-1] < df['Final_LB'].iloc[i-1]:
            df.loc[df.index[i], 'Final_LB'] = df['Basic_LB'].iloc[i]
        else:
            df.loc[df.index[i], 'Final_LB'] = df['Final_LB'].iloc[i-1]
            
        # Direction Logic
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
        st.error("डेटा नहीं मिला! कृपया सही टिकर डालें (उदा. RELIANCE.NS)")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success("डेटा सफलतापूर्वक फेच हुआ! प्रोसेसिंग जारी है...")
        
        # Calculate Supertrend
        df_result = calculate_supertrend(data, st_length, st_multiplier)
        
        # --- GENERATE TRADES & BACKTEST ---
        df_result['Signal'] = df_result['Direction'].diff() # Detect crossovers
        
        trades = []
        in_position = False
        buy_price = 0
        
        for index, row in df_result.iterrows():
            if row['Signal'] == 2: # Trend turned Green (BUY)
                if not in_position:
                    buy_price = row['Close']
                    in_position = True
                    trades.append({'Type': 'BUY', 'Price': buy_price, 'Time': index})
            elif row['Signal'] == -2: # Trend turned Red (SELL/EXIT)
                if in_position:
                    sell_price = row['Close']
                    pnl = ((sell_price - buy_price) / buy_price) * 100
                    in_position = False
                    trades.append({'Type': 'SELL', 'Price': sell_price, 'Time': index, 'PnL%': pnl})

        # --- CALCULATE PERFOMANCE METRICS ---
        st.subheader("📊 Performance Report")
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
                
            # Show Detailed Trade Log
            st.write("### 📝 Detailed Trade Log (क्लोज्ड ट्रेड्स लिस्ट)")
            st.dataframe(trades_df[['Time', 'Price', 'PnL%']])
        else:
            st.warning("इस अवधि में कोई कम्प्लीट Buy-and-Sell ट्रेड नहीं मिला। कृपया डेटा पीरियड बढ़ाएं या सेटिंग्स बदलें।")
            
        # Line Chart of Stock Close vs Supertrend
        st.write("### 📉 Stock Price vs Supertrend Line")
        st.line_chart(df_result[['Close', 'Supertrend']])

except Exception as e:
    st.error(f"सिस्टम एरर: {e}")
