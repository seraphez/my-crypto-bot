import streamlit as st
import ccxt
import time
from datetime import datetime
import requests

# 1. 基礎設定 (取消過多 CSS)
st.set_page_config(page_title="Crypto Dashboard", layout="wide")
if "ai_report" not in st.session_state: st.session_state.ai_report = ""

exchange = ccxt.okx()

st.title("🏹 專業操盤儀表板")

# 2. 側邊欄：基礎設定
st.sidebar.header("⚙️ 設定")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
fav_symbols = st.sidebar.multiselect("自選幣種", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"], default=["BTC/USDT", "ETH/USDT"])

# 3. 佈局：分成三列，完全獨立
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.header("🎯 自選監控")
    fav_placeholder = st.empty()

with col2:
    st.header("🚨 爆量雷達")
    anomaly_placeholder = st.empty()

with col3:
    st.header("🔬 AI 復盤中心")
    replay_coin = st.text_input("輸入幣種", value="BTC")
    if st.button("啟動復盤"):
        # 簡單的 API 呼叫，顯示在下方
        if api_key:
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
            prompt = f"分析 {replay_coin} 的主力心理與操作建議。"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
            st.session_state.ai_report = res.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "分析失敗")
        else:
            st.session_state.ai_report = "請輸入 API Key"
    st.write(st.session_state.ai_report)

# 4. 主循環
while True:
    try:
        tickers = exchange.fetch_tickers()
        
        # 更新自選資料
        with fav_placeholder.container():
            for s in fav_symbols:
                if s in tickers:
                    t = tickers[s]
                    st.write(f"**{s}**: {t['last']} ({t['percentage']}%)")
        
        # 更新異常資料
        with anomaly_placeholder.container():
            for s, t in tickers.items():
                if '/USDT' in s and t['quoteVolume'] and t['quoteVolume'] > 10000000 and abs(t['percentage'] or 0) > 5:
                    st.write(f"🔥 {s}: {t['percentage']}% (量: {t['quoteVolume']/1000000:.1f}M)")
        
        time.sleep(10)
    except:
        time.sleep(5)
