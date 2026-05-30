import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta  # नए इंडिकेटर्स के लिए
from backtesting import Backtest, Strategy
import streamlit.components.v1 as components

# --- PAGE CONFIG ---
st.set_page_config(page_title="Advanced Intraday Backtester", layout="wide")
st.title("🚀 Supertrend + RSI Intraday Strategy")
st.write("15-Min टाइमफ्रेम के लिए एक प्रोफेशनल और मजबूत इंट्राडे रणनीति")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Strategy Settings")
ticker = st.sidebar.text_input("Stock Ticker (Yahoo Finance)", value="SBIN.NS")
interval = st.sidebar.selectbox("Intraday Interval", options=["5m", "15m", "60m"], index=1)
period = st.sidebar.selectbox("Data Period", options=["1mo", "3mo"], index=0)

# Supertrend Parameters
st_length = st.sidebar.number_input("Supertrend Length", min_value=5, max_value=20, value=10)
st_multiplier = st.sidebar.number_input("Supertrend Multiplier", min_value=1.0, max_value=5.0, value=3.0, step=0.1)

# RSI Parameters
rsi_period = st.sidebar.number_input("RSI Period", min_value=5, max_value=30, value=14)

cash = st.sidebar.number_input("Starting Capital", value=100000)
commission_pct = st.sidebar.number_input("Brokerage & Taxes (%)", value=0.05) / 100

# --- STRATEGY LOGIC ---
class SupertrendRsiStrategy(Strategy):
    st_len = 10
    st_mult = 3.0
    rsi_len = 14
    
    def init(self):
        df = self.data.df
        
        # Pandas_ta का उपयोग करके Supertrend और RSI निकालना
        st_ind = ta.supertrend(df['High'], df['Low'], df['Close'], length=self.st_len, multiplier=self.st_mult)
        
        # Supertrend की Direction लाइन (1 मतलब Buy/Green, -1 मतलब Sell/Red)
        self.st_dir = self.I(lambda: st_ind[f"SUPERTd_{self.st_len}_{self.st_mult}"])
        self.rsi = self.I(ta.rsi, df['Close'], length=self.rsi_len)

    def next(self):
        # Current values
        current_rsi = self.rsi[-1]
        current_dir = self.st_dir[-1]
        prev_dir = self.st_dir[-2] if len(self.st_dir) > 1 else current_dir

        # BUY SIGNAL: Supertrend ग्रीन हो जाए (यानी -1 से 1 हो जाए) और RSI 50 के ऊपर हो (मजबूत मोमेंटम)
        if current_dir == 1 and prev_dir == -1 and current_rsi > 50:
            if not self.position:
                self.buy()
                
        # SELL SIGNAL: Supertrend रेड हो जाए (1 से -1 हो जाए) या RSI कमजोर हो जाए
        elif current_dir == -1 and prev_dir == 1:
            if self.position:
                self.position.close()

# --- FETCH DATA & RUN ---
st.subheader(f"📊 Running Backtest for {ticker}...")
try:
    data = yf.download(tickers=ticker, period=period, interval=interval)
    
    if data.empty:
        st.error("डेटा नहीं मिला! कृपया सही सिंबल डालें।")
    else:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success(f"सफलतापूर्वक {data.shape[0]} कैंडल्स का डेटा लोड हुआ।")
        
        # पैरामीटर्स अपडेट करना
        SupertrendRsiStrategy.st_len = st_length
        SupertrendRsiStrategy.st_mult = st_multiplier
        SupertrendRsiStrategy.st_len = rsi_period
        
        # बैकटेस्ट रन करना
        bt = Backtest(data, SupertrendRsiStrategy, cash=cash, commission=commission_pct)
        stats = bt.run()
        
        # --- DISPLAY RESULTS ---
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("### 📈 Performance Report")
            st.dataframe(stats.to_frame(name="Value"))
            
        with col2:
            st.write("### 📉 Multi-Indicator Chart")
            bt.plot(filename="temp_chart.html", open_browser=False)
            with open("temp_chart.html", "r", encoding="utf-8") as f:
                html_data = f.read()
            
            components.html(html_data, height=600, scrolling=True)

except Exception as e:
    st.error(f"एक एरर आई है: {e}")
