import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import google.generativeai as genai

# =====================================================================
# 1. 網頁頂級配置
# =====================================================================
st.set_page_config(page_title="CryptoHunter | AI 專業版", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .square-card { background-color: #161B22; border: 2px solid #30363D; border-radius: 15px; padding: 20px; margin-bottom: 15px; min-height: 250px; display: flex; flex-direction: column; }
    .coin-title { font-size: 22px; font-weight: bold; color: #00FFCC; }
    .coin-price { font-size: 28px; font-weight: bold; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 核心初始化
# =====================================================================
@st.cache_resource
def get_exchange(): return ccxt.okx()
exchange = get_exchange()

# API Key 安全讀取
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("輸入 Gemini API Key (本機測試用)", type="password")

if api_key:
    genai.configure(api_key=api_key)

# =====================================================================
# 3. 側邊欄：全功能控制台
# =====================================================================
st.sidebar.header("⚙️ 獵手配置台")
enable_ai = st.sidebar.toggle("🤖 啟用 AI 量化分析", True)
show_anomaly = st.sidebar.toggle("🚨 顯示全網異常波動", True)

# 動態選幣
@st.cache_data(ttl=3600)
def get_symbols():
    m = exchange.load_markets()
    return sorted([s for s in m.keys() if s.endswith('/USDT') and ':' not in s])

all_symbols = get_symbols()
fav_cryptos = st.sidebar.multiselect("🎯 自選監控幣種", all_symbols, default=["BTC/USDT", "ETH/USDT"])

# =====================================================================
# 4. 功能邏輯
# =====================================================================
def get_ai_report(coin, price, change, signal):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"請分析 {coin}，現價 {price}，漲跌 {change}%，訊號 {signal}。給兩句建議。")
        return response.text
    except Exception as e:
        return f"AI 連線中... ({e})"

# =====================================================================
# 5. 主畫面渲染
# =====================================================================
st.title("🏹 CryptoHunter AI 專業操盤室")
placeholder = st.empty()

while True:
    try:
        tickers = exchange.fetch_tickers()
        fav_data = [t for s, t in tickers.items() if s in fav_cryptos]
        anomaly_data = [t for s, t in tickers.items() if s.endswith('/USDT') and (abs(t['percentage'] or 0) > 6)]

        with placeholder.container():
            # 區塊 A：異常波動報告 (僅在選單啟用時顯示)
            if show_anomaly:
                st.subheader("🚨 全網異常波動快報")
                anom_df = pd.DataFrame([{"幣種": s, "漲跌": t['percentage']} for s, t in zip(anomaly_data, anomaly_data)])
                if not anom_df.empty: st.dataframe(anom_df.head(5), use_container_width=True)
                else: st.success("市場平穩")
            
            # 區塊 B：自選監控
            st.subheader("🎯 自選監控面板")
            cols = st.columns(3)
            for i, ticker in enumerate(fav_data):
                with cols[i % 3]:
                    st.markdown(f"""
                        <div class="square-card">
                            <div class="coin-title">🪙 {ticker['symbol']}</div>
                            <div class="coin-price">${ticker['last']:,}</div>
                            <div>漲跌: {ticker['percentage']}%</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if enable_ai and api_key:
                        st.info(get_ai_report(ticker['symbol'], ticker['last'], ticker['percentage'], "強勢"))
        
        time.sleep(5)
    except Exception as e:
        st.error(f"數據更新中: {e}")
        time.sleep(5)
