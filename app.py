import streamlit as st
import pandas as pd
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import streamlit.components.v1 as components

# --- PAGE CONFIG ---
st.set_page_config(page_title="15-Min Intraday Backtester", layout="wide")
st.title("📊 15-Minute Intraday Strategy Backtester")
st.write("यह डैशबोर्ड विशेष रूप से 15-Min टाइमफ्रेम पर बैकटेस्टिंग के लिए कस्टमाइज्ड है।")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔧 Settings")
ticker = st.sidebar.text_input("Stock Ticker (Yahoo Finance)", value="RELIANCE.NS")

# Default 15m और 1mo सेट किया है ताकि इंट्राडे का पर्याप्त डेटा मिले
interval = st.sidebar.selectbox("Intraday Interval", options=["1m", "5m", "15m", "60m"], index=2)
period = st.sidebar.selectbox("Data Period", options=["5d", "1mo", "3mo"], index=1)

# Strategy Parameters (EMA Crossover Strategy - जो 15m पर बेस्ट काम करती है)
fast_ema_period = st.sidebar.number_input("Fast EMA (Short term)", min_value=3, max_value=50, value=9)
slow_ema_period = st.sidebar.number_input("Slow EMA (Long term)", min_value=10, max_value=200, value=21)

cash = st.sidebar.number_input("Starting Capital (INR/USD)", value=100000)
commission_pct = st.sidebar.number_input("Brokerage & Taxes (%)", value=0.05) / 100

# --- EMA CALCULATION ---
def EMA(df, period):
    return df['Close'].ewm(span=period, adjust=False).mean()

# --- DEFINE 15-MIN STRATEGY ---
class EmaCrossStrategy(Strategy):
    fast_p = 9
    slow_p = 21
    
    def init(self):
        # Indicators calculate करें
        self.fast_ema = self.I(EMA, self.data.df, self.fast_p)
        self.slow_ema = self.I(EMA, self.data.df, self.slow_p)

    def next(self):
        # 15-min चार्ट पर जब Fast EMA ऊपर क्रॉस करे -> BUY
        if crossover(self.fast_ema, self.slow_ema):
            self.buy()
        # जब Fast EMA नीचे क्रॉस करे -> Close Position / SELL
        elif crossover(self.slow_ema, self.fast_ema):
            self.position.close()

# --- FETCH DATA & RUN ---
st.subheader(f"📈 Fetching 15-Min Data for {ticker}...")
try:
    # yfinance से डेटा फेच करना
    data = yf.download(tickers=ticker, period=period, interval=interval)
    
    if data.empty:
        st.error("डेटा नहीं मिला! कृपया सही Ticker सिंबल डालें (जैसे: SBIN.NS, TATAMOTORS.NS)")
    else:
        # Multi-index columns clean-up
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        st.success(f"पैक किया गया डेटा: {data.shape[0]} कैंडल्स लोड हुईं।")
        
        # रणनीति के पैरामीटर्स को यूजर इनपुट से अपडेट करना
        EmaCrossStrategy.fast_p = fast_ema_period
        EmaCrossStrategy.slow_p = slow_ema_period
        
        # बैकटेस्ट रन करना
        bt = Backtest(data, EmaCrossStrategy, cash=cash, commission=commission_pct)
        stats = bt.run()
        
        # --- DISPLAY RESULTS ---
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("### 📊 Performance Metrics")
            metrics_df = pd.DataFrame(stats, columns=["Value"])
            
            # महत्वपूर्ण मैट्रिक्स दिखाना
            st.dataframe(metrics_df.loc[[
    'Start', 'End', 'Duration', 'Exposure Time [%]', 
    'Equity Final [$]', 'Return [%]', 'Buy & Hold Return [%]', 
    'Max. Drawdown [%]', 'Win Rate [%]', '# Trades'       # <-- इसे अपडेट किया है
           ]])
        with col2:
            st.write("### 📉 15-Min Interactive Chart")
            # HTML चार्ट जेनरेट करके Streamlit में दिखाना
            bt.plot(filename="temp_chart.html", open_browser=False)
            with open("temp_chart.html", "r", encoding="utf-8") as f:
                html_data = f.read()
            
            components.html(html_data, height=600, scrolling=True)

except Exception as e:
    st.error(f"एक एरर आई है: {e}")
