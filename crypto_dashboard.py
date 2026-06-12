import streamlit as st
import ccxt
import pandas as pd
import time
from datetime import datetime
import google.generativeai as genai

# 1. 網頁頂級配置
st.set_page_config(page_title="CryptoHunter | AI 智能獵手", layout="wide")

# 2. 科技感 CSS 注入
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .square-card {
        background-color: #161B22; border: 2px solid #30363D; border-radius: 15px;
        padding: 20px; margin-bottom: 20px; min-height: 250px;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .coin-title { font-size: 22px; font-weight: bold; color: #00FFCC; }
    .coin-price { font-size: 28px; font-weight: bold; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

# 3. 交易所與 AI 初始化
@st.cache_resource
def get_exchange():
    return ccxt.okx()

exchange = get_exchange()

# 從 Streamlit 雲端讀取 API Key (最安全的做法)
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# 4. 核心邏輯函數
def get_signal(current, high, low):
    mid = (high + low) / 2
    if current > mid * 1.01: return "🟢 推薦開多", "#00FF66"
    if current < mid * 0.99: return "🔴 推薦開空", "#FF3366"
    return "⚪ 觀望", "#888888"

def get_ai_report(coin, price, signal):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(f"請分析 {coin}，現價 {price}，訊號為 {signal}。給我兩句簡短操作建議。")
        return response.text
    except: return "AI 引擎暫時無法連線。"

# 5. 主程式
st.title("🏹 CryptoHunter AI 智能獵手")
fav_cryptos = st.sidebar.multiselect("🎯 設定自選幣", ["BTC/USDT", "ETH/USDT", "SOL/USDT"], default=["BTC/USDT"])
enable_ai = st.sidebar.toggle("🤖 啟動 AI 分析", True)

placeholder = st.empty()

while True:
    try:
        tickers = exchange.fetch_tickers()
        with placeholder.container():
            cols = st.columns(3)
            for i, symbol in enumerate(fav_cryptos):
                if symbol in tickers:
                    t = tickers[symbol]
                    signal, color = get_signal(t['last'], t['high'], t['low'])
                    
                    with cols[i % 3]:
                        st.markdown(f"""
                            <div class="square-card">
                                <div class="coin-title">🪙 {symbol}</div>
                                <div class="coin-price">${t['last']:,}</div>
                                <div style="color:{color}; font-weight:bold;">{signal}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        if enable_ai and api_key:
                            st.info(get_ai_report(symbol, t['last'], signal))
        time.sleep(5)
    except Exception as e:
        st.error(f"連線錯誤: {e}")
        time.sleep(5)
