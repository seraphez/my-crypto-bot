import streamlit as st
import ccxt
import time
from datetime import datetime

# 設定頁面為寬版
st.set_page_config(page_title="CryptoHunter Dashboard", layout="wide")

exchange = ccxt.okx()

# 標題
st.title("🏹 專業操盤儀表板")

# 側邊欄設定
st.sidebar.header("⚙️ 設定")
fav_symbols = st.sidebar.multiselect("選擇監控幣種", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"], default=["BTC/USDT", "SOL/USDT"])

# 建立左右兩大區域
col_left, col_right = st.columns([1, 1])

# --- 左側：自選監控與復盤 ---
with col_left:
    st.header("🎯 自選幣核心監控")
    
    # 使用 Tabs 分頁讓界面不擁擠
    tab1, tab2 = st.tabs(["📊 即時監控", "🔬 AI 復盤鑑定"])
    
    with tab1:
        st.write(f"⏱ 同步時間：{datetime.now().strftime('%H:%M:%S')}")
        fav_placeholder = st.empty()
    
    with tab2:
        st.subheader("啟動 AI 獵手復盤")
        replay_input = st.text_input("輸入要復盤的幣種代號", value="BTC")
        if st.button("啟動 AI 復盤鑑定"):
            st.info(f"正在對 {replay_input} 進行量化結構調研...")
            # 這裡放入您原本的 AI 請求邏輯

# --- 右側：全網異常提醒 ---
with col_right:
    st.header("🚨 全網【突發爆量異常】提醒")
    st.caption("🔥 自動鎖定 24h 成交額 > 10M 且波動 > 5% 的標的")
    anomaly_placeholder = st.empty()

# --- 主循環 ---
while True:
    try:
        tickers = exchange.fetch_tickers()
        
        # 渲染左側自選
        with fav_placeholder.container():
            for s in fav_symbols:
                if s in tickers:
                    t = tickers[s]
                    st.write(f"**{s}**: {t['last']} ({t['percentage']}%)")
        
        # 渲染右側異常
        with anomaly_placeholder.container():
            anomalies = []
            for s, t in tickers.items():
                if '/USDT' in s and t['quoteVolume'] and t['quoteVolume'] > 10000000 and abs(t['percentage'] or 0) > 5:
                    anomalies.append(f"🔥 {s.replace('/USDT', '')} | 漲跌: {t['percentage']}% | 量: {t['quoteVolume']/1000000:.1f}M")
            
            for item in anomalies[:10]: # 限制顯示數量避免過長
                st.write(item)
        
        time.sleep(10)
    except:
        time.sleep(5)
