import streamlit as st
import ccxt
import time
from datetime import datetime
import requests

# 1. 基礎配置
st.set_page_config(page_title="Crypto Dashboard", layout="wide")
if "ai_triggered" not in st.session_state: st.session_state.ai_triggered = False
if "report" not in st.session_state: st.session_state.report = ""

# 2. 交易所
exchange = ccxt.okx()

# 3. 側邊欄 (自選幣區)
st.sidebar.header("🎯 自選監控")
all_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
fav_cryptos = st.sidebar.multiselect("選擇幣種", all_symbols, default=["BTC/USDT", "ETH/USDT"])
api_key = st.sidebar.text_input("Gemini API Key", type="password")

# 4. 異常提醒與復盤窗口 (放在右上角或主頁上方)
st.title("🏹 操盤控制台")
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🪙 自選幣即時行情")
    fav_placeholder = st.empty()

with col2:
    st.subheader("🚨 異常與復盤")
    anomaly_placeholder = st.empty()
    st.markdown("---")
    replay_coin = st.text_input("輸入幣種進行 AI 復盤", value="BTC")
    if st.button("🚀 啟動復盤"):
        st.session_state.ai_triggered = True
        st.session_state.replay_coin = replay_coin

# 5. 主循環
while True:
    try:
        tickers = exchange.fetch_tickers()
        fav_data = []
        anomalies = []
        
        for s in fav_cryptos:
            if s in tickers: fav_data.append(tickers[s])
            
        for s, t in tickers.items():
            if '/USDT' in s and t['quoteVolume'] and t['quoteVolume'] > 10000000 and abs(t['percentage'] or 0) > 5:
                anomalies.append(f"🔥 {s}: {t['percentage']}%")

        # 渲染畫面
        with fav_placeholder.container():
            for d in fav_data:
                st.write(f"**{d['symbol']}**: {d['last']} ({d['percentage']}%)")
        
        with anomaly_placeholder.container():
            for a in anomalies[:5]: st.warning(a)
            
        # AI 復盤邏輯 (鎖定狀態)
        if st.session_state.ai_triggered:
            st.session_state.ai_triggered = False
            if api_key:
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
                prompt = f"分析 {st.session_state.replay_coin} 的主力心理與操作建議。"
                res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                st.session_state.report = res.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "Error")
            else:
                st.session_state.report = "請輸入 API Key"
        
        if st.session_state.report:
            st.error(st.session_state.report)
            
        time.sleep(10)
    except Exception as e:
        time.sleep(5)
