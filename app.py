import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Advanced Backtester", layout="wide")

st.title("🚀 इंट्राडे बैकटेस्टिंग (ORB + 20 EMA)")

# इनपुट फील्ड्स
ticker = st.sidebar.text_input("स्टॉक सिंबल", "RELIANCE.NS")
stop_loss_pts = st.sidebar.number_input("स्टॉप-लॉस पॉइंट्स", value=10)
rr_ratio = st.sidebar.slider("रिस्क-रिवॉर्ड रेश्यो", 1.0, 3.0, 1.5)

if st.button("बैकटेस्ट शुरू करें"):
    # 1. डेटा डाउनलोड
    df = yf.download(ticker, period="5d", interval="5m")
    
    if df.empty:
        st.error("डेटा नहीं मिला! कृपया सही सिंबल डालें।")
        st.stop()

    # 2. डेटा क्लीनिंग (NaN हटाना)
    df = df.dropna()
    
    # 3. 20 EMA की गणना
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['Time'] = df.index.time
    
    # 4. सुबह की रेंज का डेटा सुरक्षित करना
    morning_data = df[df['Time'] <= pd.to_datetime("10:30").time()]
    
    if morning_data.empty:
        st.warning("10:30 AM तक का पर्याप्त डेटा नहीं है।")
        st.stop()
        
    m_high = float(morning_data['High'].max())
    m_low = float(morning_data['Low'].min())
    
    # 5. बैकटेस्टिंग लॉजिक
    results = []
    post_data = df[df['Time'] > pd.to_datetime("10:30").time()]
    
    for index, row in post_data.iterrows():
        # वैल्यूज़ को float में बदलना ताकि एरर न आए
        close_val = float(row['Close'])
        ema_val = float(row['EMA_20'])
        
        # BUY Logic: प्राइस रेंज के ऊपर और EMA के ऊपर
        if close_val > m_high and close_val > ema_val:
            target = close_val + (stop_loss_pts * rr_ratio)
            sl = close_val - stop_loss_pts
            # चेक करें कि हाई ने टारगेट हिट किया या नहीं
            result = "PROFIT" if float(row['High']) >= target else "LOSS"
            results.append({'Time': row['Time'], 'Type': 'BUY', 'Status': result})
            break 
            
        # SELL Logic: प्राइस रेंज के नीचे और EMA के नीचे
        elif close_val < m_low and close_val < ema_val:
            target = close_val - (stop_loss_pts * rr_ratio)
            sl = close_val + stop_loss_pts
            result = "PROFIT" if float(row['Low']) <= target else "LOSS"
            results.append({'Time': row['Time'], 'Type': 'SELL', 'Status': result})
            break

    # 6. रिपोर्ट दिखाना
    if results:
        st.write("### ट्रेड रिजल्ट्स", pd.DataFrame(results))
    else:
        st.info("आज के लिए कोई सेटअप नहीं मिला।")

    st.line_chart(df[['Close', 'EMA_20']])
