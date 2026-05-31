import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Advanced Backtester with EMA", layout="wide")

st.title("🚀 इंट्राडे बैकटेस्टिंग (ORB + 20 EMA फिल्टर)")

# इनपुट फील्ड्स
ticker = st.sidebar.text_input("स्टॉक सिंबल", "RELIANCE.NS")
stop_loss_pts = st.sidebar.number_input("स्टॉप-लॉस पॉइंट्स", value=10)
rr_ratio = st.sidebar.slider("रिस्क-रिवॉर्ड रेश्यो", 1.0, 3.0, 1.5)

if st.button("बैकटेस्ट शुरू करें"):
    # डेटा डाउनलोड
    df = yf.download(ticker, period="5d", interval="5m")
    
    # 20 EMA की गणना
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['Time'] = df.index.time
    
    # सुबह की रेंज
    morning_data = df[df['Time'] <= pd.to_datetime("10:30").time()]
    m_high = morning_data['High'].max()
    m_low = morning_data['Low'].min()
    
    results = []
    post_data = df[df['Time'] > pd.to_datetime("10:30").time()]
    
    for index, row in post_data.iterrows():
        # BUY Logic: प्राइस रेंज के ऊपर हो AND प्राइस 20 EMA के ऊपर हो
        if row['Close'] > m_high and row['Close'] > row['EMA_20']:
            result = "PROFIT" if row['High'] >= (row['Close'] + (stop_loss_pts * rr_ratio)) else "LOSS"
            results.append({'Time': row['Time'], 'Type': 'BUY', 'Status': result})
            break 
            
        # SELL Logic: प्राइस रेंज के नीचे हो AND प्राइस 20 EMA के नीचे हो
        elif row['Close'] < m_low and row['Close'] < row['EMA_20']:
            result = "PROFIT" if row['Low'] <= (row['Close'] - (stop_loss_pts * rr_ratio)) else "LOSS"
            results.append({'Time': row['Time'], 'Type': 'SELL', 'Status': result})
            break

    # रिपोर्टिंग
    if results:
        st.write("### ट्रेड रिजल्ट्स", pd.DataFrame(results))
    else:
        st.warning("कोई भी ट्रेड 20 EMA फिल्टर के साथ नहीं मिला।")

    st.line_chart(df[['Close', 'EMA_20']])
