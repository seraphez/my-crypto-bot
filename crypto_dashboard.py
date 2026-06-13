import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from groq import Groq
import os

# --- 1. 頁面風格 ---
st.set_page_config(page_title="🌸 SMC 櫻花獵鯨網", layout="centered")
st.markdown("""
    <style>
        .stApp { background-color: #121214; color: #F8F9FA; }
        h1 { color: #FFB7C5 !important; }
        div.stButton > button:first-child { background: linear-gradient(135deg, #FFB7C5, #FFD1DC); border-radius: 8px; width: 100%; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🌸 獵鯨網 · 暮櫻實戰系統")

# --- 2. 安全金鑰處理 (線上讀 Secrets，本地防呆) ---
SAFE_GROQ_API_KEY = os.getenv("GROQ_API_KEY")
try:
    if "GROQ_API_KEY" in st.secrets:
        SAFE_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    pass

if not SAFE_GROQ_API_KEY:
    st.sidebar.warning("⚠️ 檢測到本地環境，請輸入 API Key：")
    SAFE_GROQ_API_KEY = st.sidebar.text_input("Groq API Key", type="password")

# --- 3. 數據與分析引擎 ---
def fetch_data(symbol, tf):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        df['rsi'] = ta.rsi(df['c'], length=14)
        return {"price": round(df['c'].iloc[-1], 4), "rsi": round(df['rsi'].iloc[-1], 2), "high": round(df['h'].max(), 4), "low": round(df['l'].min(), 4)}
    except:
        return {"price": 0, "rsi": 50, "high": 0, "low": 0}

# --- 4. 主程式 ---
target_coin = st.sidebar.selectbox("標的", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
if st.button("🌸 啟動掃描"):
    if not SAFE_GROQ_API_KEY:
        st.error("請提供 API Key")
    else:
        with st.spinner("連線幣安與 AI 分析中..."):
            d3m = fetch_data(target_coin, "3m")
            d15m = fetch_data(target_coin, "15m")
            d1h = fetch_data(target_coin, "1h")
            d4h = fetch_data(target_coin, "4h")
            
            st.metric("當前實時市價", f"${d3m['price']} USDT")
            
            client = Groq(api_key=SAFE_GROQ_API_KEY)
            prompt = f"分析 {target_coin}，目前價格 {d3m['price']}，15m RSI {d15m['rsi']}。請給出進場點位與止損線。"
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user", "content": prompt}])
            st.markdown(res.choices[0].message.content)
