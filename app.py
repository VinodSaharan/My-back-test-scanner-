import streamlit as st
import pandas as pd

st.set_page_config(page_title="Advanced Backtester", layout="wide")

st.title("🚀 एडवांस्ड इंट्राडे बैकटेस्टिंग टूल")

uploaded_file = st.sidebar.file_uploader("अपनी CSV फाइल अपलोड करें", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    # यह सुनिश्चित करें कि CSV में Date और Time कॉलम सही फॉर्मेट में हैं
    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.time
    
    st.sidebar.write("### रिस्क सेटिंग्स")
    rr_ratio = st.sidebar.slider("रिस्क-रिवॉर्ड रेश्यो", 1.0, 3.0, 1.5)
    stop_loss_pts = st.sidebar.number_input("स्टॉप-लॉस पॉइंट्स", value=10)

    if st.button("बैकटेस्ट रन करें"):
        morning_data = df[df['Time'] <= pd.to_datetime("10:30").time()]
        m_high = morning_data['High'].max()
        m_low = morning_data['Low'].min()
        
        results = []
        post_data = df[df['Time'] > pd.to_datetime("10:30").time()]
        
        for index, row in post_data.iterrows():
            # BUY Logic
            if row['Close'] > m_high:
                entry = row['Close']
                sl = entry - stop_loss_pts
                target = entry + (stop_loss_pts * rr_ratio)
                # यह चेक करना कि टारगेट या SL हिट हुआ या नहीं
                result = "PROFIT" if row['High'] >= target else ("LOSS" if row['Low'] <= sl else "OPEN")
                results.append({'Time': row['Time'], 'Type': 'BUY', 'Price': entry, 'Status': result})
                break # एक बार में एक ही ट्रेड का उदाहरण
            
            # SELL Logic
            elif row['Close'] < m_low:
                entry = row['Close']
                sl = entry + stop_loss_pts
                target = entry - (stop_loss_pts * rr_ratio)
                result = "PROFIT" if row['Low'] <= target else ("LOSS" if row['High'] >= sl else "OPEN")
                results.append({'Time': row['Time'], 'Type': 'SELL', 'Price': entry, 'Status': result})
                break

        # रिजल्ट का विश्लेषण
        res_df = pd.DataFrame(results)
        st.write("### ट्रेड रिजल्ट्स", res_df)
        
        # Win Rate कैलकुलेशन
        if not res_df.empty:
            wins = len(res_df[res_df['Status'] == "PROFIT"])
            win_rate = (wins / len(res_df)) * 100
            st.metric("Win Rate", f"{win_rate:.2f}%")
        else:
            st.warning("कोई ट्रेड सिग्नल नहीं मिला।")

else:
    st.info("कृपया डेटा फाइल अपलोड करें ताकि हम बैकटेस्ट शुरू कर सकें।")
