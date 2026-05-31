import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Direct Backtester", layout="wide")

st.title("🚀 बिना CSV के लाइव बैकटेस्टिंग टूल")

# 1. इनपुट फील्ड्स
ticker = st.sidebar.text_input("स्टॉक सिंबल (जैसे RELIANCE.NS)", "RELIANCE.NS")
stop_loss_pts = st.sidebar.number_input("स्टॉप-लॉस पॉइंट्स", value=10)
rr_ratio = st.sidebar.slider("रिस्क-रिवॉर्ड रेश्यो", 1.0, 3.0, 1.5)

if st.button("डेटा डाउनलोड और बैकटेस्ट करें"):
    # 2. Yahoo Finance से डेटा डाउनलोड करें
    df = yf.download(ticker, period="5d", interval="5m")
    
    # टाइमजोन और फॉर्मेटिंग
    df.index = pd.to_datetime(df.index)
    df['Time'] = df.index.time
    
    # 10:30 AM तक का डेटा (रेंज निकालने के लिए)
    morning_data = df[df['Time'] <= pd.to_datetime("10:30").time()]
    m_high = morning_data['High'].max()
    m_low = morning_data['Low'].min()
    
    st.write(f"### {ticker} के लिए 10:30 AM की रेंज: High={m_high:.2f}, Low={m_low:.2f}")

    # 3. बैकटेस्टिंग लॉजिक
    results = []
    post_data = df[df['Time'] > pd.to_datetime("10:30").time()]
    
    for index, row in post_data.iterrows():
        # BUY Logic
        if row['Close'] > m_high:
            entry = row['Close']
            target = entry + (stop_loss_pts * rr_ratio)
            sl = entry - stop_loss_pts
            # यहाँ हम यह चेक कर रहे हैं कि क्या उस कैंडल में टारगेट/SL हिट हुआ
            result = "PROFIT" if row['High'] >= target else ("LOSS" if row['Low'] <= sl else "NEUTRAL")
            results.append({'Time': row['Time'], 'Type': 'BUY', 'Status': result})
            break 
            
        # SELL Logic
        elif row['Close'] < m_low:
            entry = row['Close']
            target = entry - (stop_loss_pts * rr_ratio)
            sl = entry + stop_loss_pts
            result = "PROFIT" if row['Low'] <= target else ("LOSS" if row['High'] >= sl else "NEUTRAL")
            results.append({'Time': row['Time'], 'Type': 'SELL', 'Status': result})
            break

    # 4. रिपोर्ट
    if results:
        res_df = pd.DataFrame(results)
        st.write("### ट्रेड रिजल्ट्स", res_df)
    else:
        st.warning("10:30 के बाद कोई एंट्री नहीं मिली।")

    st.line_chart(df['Close'])
