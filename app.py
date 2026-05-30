import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="High-Return Only Sell", layout="wide")
st.title("⚡ High-Return ONLY SHORT/SELL Strategy (3-Month Data)")
st.write("कम रिटर्न की समस्या को दूर करने के लिए बनाई गई एक फास्ट और डायनेमिक शॉर्टिंग स्ट्रेटजी")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Settings")
ticker = st.sidebar.text_input("Stock Ticker", value="TATAMOTORS.NS")

# Fast Parameters for High Return
st_length = st.sidebar.number_input("Supertrend Length (ATR)", min_value=3, value=7) # छोटा किया फॉर फास्ट सिग्नल्स
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, value=1.5, step=0.1) # 1.5 किया ताकि छोटा सा फॉल भी पकड़े
ema_period = st.sidebar.number_input("Fast EMA Period", min_value=5, value=21) # 21 EMA किया

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

# --- PURE PANDAS FAST INDICATORS ---
def calculate_indicators(df, st_len=7, st_mult=1.5, ema_len=21):
    df = df.copy()
    
    # Fast EMA
    df['EMA_Fast'] = df['Close'].ewm(span=ema_len, adjust=False).mean()
    
    # Fast Supertrend Calculation
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
        st.error("डेटा नहीं मिला!")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success("पिछले 3 महीने का डेटा सफलतापूर्वक लोड और कंबाइन हो गया!")
        
        df_result = calculate_indicators(data, st_length, st_multiplier, ema_period)
        
        # --- HIGH SPEED SHORT LOGIC ---
        trades = []
        in_short = False
        entry_price = 0
        entry_time = None
        
        for i in range(1, len(df_result)):
            row = df_result.iloc[i]
            prev_row = df_result.iloc[i-1]
            index = df_result.index[i]
            
            if in_short:
                # EXIT SHORT: जैसे ही सुपरट्रेंड ग्रीन हो या प्राइस 21 EMA के ऊपर निकले (फास्ट एक्जिट)
                if row['Direction'] == 1 or row['Close'] > row['EMA_Fast']:
                    pnl = ((entry_price - row['Close']) / entry_price) * 100
                    trades.append({'Trade Type': 'SHORT (Sell)', 'Entry Time': entry_time, 'Exit Time': index, 'Entry Price': entry_price, 'Exit Price': row['Close'], 'PnL%': pnl})
                    in_short = False
            else:
                # ENTRY SHORT: जैसे ही सुपरट्रेंड रेड हो और प्राइस 21 EMA के नीचे हो (नो RSI डिले)
                if prev_row['Direction'] == 1 and row['Direction'] == -1:
                    if row['Close'] < row['EMA_Fast']:
                        in_short = True
                        entry_price = row['Close']
                        entry_time = index

        # --- DISPLAY RESULTS ---
        st.subheader("📊 Performance Report")
        col1, col2 = st.columns(2)
        
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            
            total_trades = len(trades_df)
            win_trades = len(trades_df[trades_df['PnL%'] > 0])
            win_rate = (win_trades / total_trades) * 100
            total_return = trades_df['PnL%'].sum()
            final_equity = cash * (1 + (total_return/100))
            
            with col1:
                st.metric(label="Total Return (%) 🔥", value=f"{total_return:.2f}%", delta=f"{total_return:.2f}%")
                st.metric(label="Final Estimated Capital", value=f"₹{final_equity:,.2f}")
                
            with col2:
                st.metric(label="Total Closed Trades", value=total_trades)
                st.metric(label="Win Rate (%)", value=f"{win_rate:.2f}%")
                
            st.write("### 📝 Fast Sell Trades Log")
            st.dataframe(trades_df[['Entry Time', 'Exit Time', 'Entry Price', 'Exit Price', 'PnL%']])
        else:
            st.warning("कोई ट्रेड नहीं मिला। कृपया साइडबार से पैरामीटर्स बदलें।")
            
        # Charts
        st.write("### 📉 3-Month Price vs Fast Supertrend & 21 EMA")
        st.line_chart(df_result[['Close', 'Supertrend', 'EMA_Fast']])

except Exception as e:
    st.error(f"सिस्टम एरर: {e}")
