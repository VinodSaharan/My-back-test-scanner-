import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Professional Backtester", layout="wide")

st.title("📊 प्रोफेशनल इंट्राडे बैकटेस्टिंग इंजन")

# इनपुट
ticker = st.sidebar.text_input("स्टॉक सिंबल", "RELIANCE.NS")
stop_loss_pts = st.sidebar.number_input("स्टॉप-लॉस (पॉइंट्स)", value=10)
rr_ratio = st.sidebar.slider("रिस्क-रिवॉर्ड रेश्यो", 1.0, 3.0, 1.5)

if st.button("पूरे दिन का बैकटेस्ट रन करें"):
    # डेटा डाउनलोड
    df = yf.download(ticker, period="5d", interval="5m").dropna()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['Time'] = df.index.time
    
    # रेंज कैलकुलेशन
    morning_data = df[df['Time'] <= pd.to_datetime("10:30").time()]
    m_high = float(morning_data['High'].max())
    m_low = float(morning_data['Low'].min())
    
    # बैकटेस्टिंग लॉजिक (पूरे दिन के लिए)
    trades = []
    post_data = df[df['Time'] > pd.to_datetime("10:30").time()]
    
    in_trade = False
    for index, row in post_data.iterrows():
        close = float(row['Close'])
        ema = float(row['EMA_20'])
        
        if not in_trade:
            # BUY एंट्री
            if close > m_high and close > ema:
                trades.append({'Time': row['Time'], 'Type': 'BUY', 'Price': close, 'Result': 'EXECUTED'})
                in_trade = True
            # SELL एंट्री
            elif close < m_low and close < ema:
                trades.append({'Time': row['Time'], 'Type': 'SELL', 'Price': close, 'Result': 'EXECUTED'})
                in_trade = True
        
        # ट्रेड क्लोजिंग लॉजिक (सरल मॉडल: अगले सिग्नल पर या दिन के अंत में)
        elif in_trade:
            if trades[-1]['Type'] == 'BUY':
                if float(row['Low']) <= (trades[-1]['Price'] - stop_loss_pts):
                    trades[-1]['Result'] = 'LOSS'
                    in_trade = False
                elif float(row['High']) >= (trades[-1]['Price'] + (stop_loss_pts * rr_ratio)):
                    trades[-1]['Result'] = 'PROFIT'
                    in_trade = False
            else: # SELL क्लोजिंग
                if float(row['High']) >= (trades[-1]['Price'] + stop_loss_pts):
                    trades[-1]['Result'] = 'LOSS'
                    in_trade = False
                elif float(row['Low']) <= (trades[-1]['Price'] - (stop_loss_pts * rr_ratio)):
                    trades[-1]['Result'] = 'PROFIT'
                    in_trade = False

    # रिपोर्टिंग
    if trades:
        res_df = pd.DataFrame(trades)
        st.write("### ट्रेड हिस्ट्री", res_df)
        
        # मेट्रिक्स
        wins = len(res_df[res_df['Result'] == 'PROFIT'])
        total = len(res_df[res_df['Result'].isin(['PROFIT', 'LOSS'])])
        win_rate = (wins/total * 100) if total > 0 else 0
        
        col1, col2 = st.columns(2)
        col1.metric("Win Rate", f"{win_rate:.2f}%")
        col2.metric("कुल ट्रेड", total)
    else:
        st.warning("कोई एंट्री नहीं मिली।")

    # चार्ट विज़ुअलाइज़ेशन
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], name="20 EMA"))
    st.plotly_chart(fig, use_container_width=True)
