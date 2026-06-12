import streamlit as st
import ccxt
import time
from datetime import datetime
import requests

# 基礎設定
st.set_page_config(page_title="CryptoHunter Pro", layout="wide")

# 初始化狀態
if "ai_report" not in st.session_state: st.session_state.ai_report = ""
if "ai_triggered" not in st.session_state: st.session_state.ai_triggered = False

exchange = ccxt.okx()

st.title("🏹 專業操盤儀表板")

# 側邊欄
st.sidebar.header("⚙️ 設定")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
fav_symbols = st.sidebar.multiselect("自選幣監控", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"], default=["BTC/USDT", "SOL/USDT"])

# 佈局
col_left, col_right = st.columns([1, 1])

# --- 左側：自選幣與復盤 ---
with col_left:
    st.header("🎯 自選幣核心監控")
    
    # 這裡放即時行情
    tickers = exchange.fetch_tickers()
    for s in fav_symbols:
        if s in tickers:
            t = tickers[s]
            st.write(f"**{s}**: {t['last']} ({t['percentage']}%)")
    
    st.markdown("---")
    st.header("🚀 AI 復盤研究室")
    replay_coin = st.text_input("輸入要復盤的幣種", value="SOL").strip().upper()
    
    if st.button("啟動 AI 獵手復盤鑑定"):
        st.session_state.ai_triggered = True
        st.session_state.replay_coin = replay_coin

# --- 右側：全網異常雷達 ---
with col_right:
    st.header("🚨 全網【突發爆量異常】雷達")
    for s, t in tickers.items():
        if '/USDT' in s and t['quoteVolume'] and t['quoteVolume'] > 10000000 and abs(t['percentage'] or 0) > 5:
            st.write(f"🔥 **{s.replace('/USDT', '')}**: {t['percentage']}% | 量: {t['quoteVolume']/1000000:.1f}M")

# --- AI 復盤執行區 (移出迴圈，由按鈕觸發) ---
if st.session_state.ai_triggered:
    st.session_state.ai_triggered = False
    if api_key:
        with st.spinner(f"正在對 {st.session_state.replay_coin} 進行量化結構調研..."):
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
            prompt = f"分析 {st.session_state.replay_coin} 的主力心理與操作建議。"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            st.session_state.ai_report = res.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "分析失敗")
    else:
        st.error("⚠️ 請先輸入 API Key")

if st.session_state.ai_report:
    st.error(f"⚔️ **AI 復盤報告 ({st.session_state.replay_coin}):**\n{st.session_state.ai_report}")

# --- 自動刷新機制 (取代 while True) ---
time.sleep(10) # 等待 10 秒
st.rerun()    # 強制頁面重整，達成自動更新效果
