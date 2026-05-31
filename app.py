import streamlit as st
import yfinance as yf
import pandas as pd

# पेज सेटअप
st.set_page_config(page_title="Intraday Dashboard", layout="wide")

st.title("📈 इंट्राडे रणनीति डैशबोर्ड")

# साइडबार - इनपुट के लिए
ticker = st.sidebar.text_input("स्टॉक सिंबल डालें (जैसे: RELIANCE.NS)", "RELIANCE.NS")
timeframe = st.sidebar.selectbox("टाइमफ्रेम चुनें", ["5m", "15m", "1h"])

# डेटा लोड करना
@st.cache_data
def get_data(ticker, period="1d", interval="5m"):
    data = yf.download(ticker, period=period, interval=interval)
    return data

if st.sidebar.button("डेटा लोड करें"):
    df = get_data(ticker, interval=timeframe)
    st.write(f"### {ticker} का चार्ट डेटा")
    st.line_chart(df['Close'])

    # सांख्यिकीय जानकारी (Stats)
    st.write("### मुख्य सांख्यिकी")
    st.metric(label="अंतिम भाव", value=f"{df['Close'].iloc[-1]:.2f}")
    
    # 20 EMA की गणना
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    st.write("### 20 EMA डेटा")
    st.line_chart(df[['Close', 'EMA_20']])
