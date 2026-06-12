import streamlit as st
import ccxt
import time
from datetime import datetime
import requests

# 1. 基礎設定
st.set_page_config(page_title="CryptoHunter Pro", layout="wide")

# 初始化 Session State
if "ai_report" not in st.session_state: st.session_state.ai_report = ""
if "replay_triggered" not in st.session_state: st.session_state.replay_triggered = False

exchange = ccxt.okx()

st.title("🏹 專業操盤儀表板")

# 2. 側邊欄：所有設定都在這
st.sidebar.header("⚙️ 核心設定")
api_key = st.sidebar.text_input("Gemini API Key", type="password")
fav_symbols = st.sidebar.multiselect("設定自選監控區", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"], default=["BTC/USDT", "SOL/USDT"])

# 3. 左右分欄排版 (左：自選/復盤，右：異常提醒)
col_left, col_right = st.columns([1, 1])

# --- 左側：自選監控與復盤區 ---
with col_left:
    st.header("🎯 自選幣核心監控")
    try:
        tickers = exchange.fetch_tickers()
        for s in fav_symbols:
            if s in tickers:
                st.write(f"🪙 **{s}**: {tickers[s]['last']} | 漲跌: {tickers[s]['percentage']}%")
    except:
        st.error("行情讀取中...")

    st.markdown("---")
    st.header("🔬 AI 復盤研究室")
    target_coin = st.text_input("輸入要復盤的幣種代號", value="BTC").strip().upper()
    if st.button("啟動 AI 獵手復盤鑑定"):
        st.session_state.replay_triggered = True
        st.session_state.target_coin = target_coin
        st.rerun()

    if st.session_state.replay_triggered:
        st.session_state.replay_triggered = False
        if api_key:
            with st.spinner(f"正在對 {st.session_state.target_coin} 進行結構分析..."):
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
                prompt = f"分析 {st.session_state.target_coin} 的主力心理與實戰操盤建議。"
                res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
                st.session_state.ai_report = res.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "分析失敗")
        else:
            st.error("⚠️ 請先在左側欄輸入 API Key")

    if st.session_state.ai_report:
        st.error(f"⚔️ **AI 實戰復盤報告 ({st.session_state.target_coin}):**\n{st.session_state.ai_report}")

# --- 右側：全網異常雷達 ---
with col_right:
    st.header("🚨 全網【爆量異動】雷達")
    st.caption("自動鎖定 24h 成交額 > 10M 且波動 > 5% 的全網標的")
    try:
        for s, t in tickers.items():
            if '/USDT' in s and t['quoteVolume'] and t['quoteVolume'] > 10000000 and abs(t['percentage'] or 0) > 5:
                st.write(f"🔥 **{s.replace('/USDT', '')}** | 漲跌: {t['percentage']}% | 成交額: {t['quoteVolume']/1000000:.1f}M USDT")
    except:
        st.info("掃描異常數據中...")

# 4. 非阻塞式更新 (10秒自動刷新一次)
time.sleep(10)
st.rerun()
